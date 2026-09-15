"""CP-SAT shift scheduler.

Given
  - month (year, month)
  - employees + weekly desired shift count
  - shift patterns (basic + exception / Wワーク)
  - hourly staffing rules (weekday/weekend-holiday × 1時間ごとの必要人数)
  - availability (unavailable / preferred)
  - LLM-derived constraints (optional)

Produce a monthly assignment that:
  * meets required staffing per (date, hour) — HARD (時間カバレッジ方式)
  * respects unavailable days — HARD
  * respects preferred days (bonus) — SOFT
  * respects each employee's weekly shift count — HARD for weekly_shifts_pinned
    employees on full (7-day) weeks, otherwise SOFT (ADR-0003, 日曜起点)
  * balances load — SOFT

必要人数(HARD) と 週回数(HARD) は両立しない週が出るため、solve() は
3段フォールバックで必ず部分解を返す（詳細は solve() のdocstring参照）。
"""

from __future__ import annotations

import calendar
import time as _time
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from typing import Any

from ortools.sat.python import cp_model

from app.services.holidays import category_for

# 目的関数の重み。平準化(S-6)を最優先にし、希望/メインシフト(S-1/S-5)は
# 「同じくらい公平な解の中での寄せ」程度の弱いタイブレーカーに留める。
# こうしないと、メインシフト偏重で特定カテゴリの枠不足に引きずられ分配が偏る。
BALANCE_WEIGHT = 50
PREFERENCE_WEIGHT = 1
MAIN_SHIFT_WEIGHT = 1  # 廃止(ADR-0002): メインシフト寄せは撤廃。参照用に残置（現在は未使用）。
# 廃止(ADR-0004): パターン統合により Wワーク寄せは撤廃。定数は参照用に残置（現在は未使用）。
DUAL_WWORK_WEIGHT = 8
# 新規採用者の想定 週勤務回数（人手不足時の推奨採用人数の計算に使用）
DEFAULT_NEW_HIRE_WEEKLY = 5
# 必要人数の不足ペナルティ重み。他のどの目的より十分大きくし、不足は最優先で潰す。
COVERAGE_SLACK_WEIGHT = 1000
# 各時間に許す過剰(surplus)の上限 α（ADR-0005）。「必要人数 ≤ 配置 ≤ 必要人数 + α」に収める。
# 短い勤務可能時間帯の従業員などを +α の枠で入れられる。過剰の暴走は α で頭打ち。
SURPLUS_TOLERANCE = 1
# 過剰1人・1時間あたりの弱ペナルティ。平準化(BALANCE_WEIGHT)より十分小さくし、
# 「誰かを働かせられる時だけ +α を使い、無駄な過剰は出さない」挙動にする。
SURPLUS_WEIGHT = 2
# 保険区分ごとの月間実働時間(時間)の下限・上限(ADR-0006)。上限 None は無制限。
# social(社会保険): 120h以上 / employment(雇用保険): 80-119h / none(なし): 79h以下。
INSURANCE_HOURS_BOUNDS: dict[str, tuple[int, int | None]] = {
    "social": (120, None),
    "employment": (80, 119),
    "none": (0, 79),
}
# 保険区分の月間時間の下限違反(不足分1時間あたり)のソフトペナルティ。
# 週回数と同格の弱い寄せにし、フォールバックで下限を緩めたときの誘導に使う。
INSURANCE_UNDER_WEIGHT = 1
# 連勤の上限（ADR-0008）。全従業員一律。生成月内の連続 MAX_CONSECUTIVE_DAYS+1 日を禁止。
MAX_CONSECUTIVE_DAYS = 4
# 確定出勤(固定カレンダーの work_hard, ADR-0009)を満たせないときのソフトペナルティ。
# 不足(=最優先)より小さく、平準化より大きくして「できる限り確定出勤を守る」寄せにする。
MANDATORY_WEIGHT = 100


@dataclass(frozen=True)
class PatternSpec:
    id: int
    code: str  # 内部の名前
    label: str  # 表示名
    start: time  # 開始時刻
    end: time  # 終了時刻
    category: str  # morning|evening|night（開始時刻から自動判定）
    rest_minutes: int = 0  # 休憩(分)。割当へスナップショットする
    worked_minutes: int = 0  # 実働(分) = スパン − 休憩。保険区分の月間時間制約に使う


@dataclass(frozen=True)
class EmployeeSpec:
    id: int
    name: str
    weekly_target: int  # 週に何回入りたいか
    hourly_wage: int
    # True なら「完全な7日週でちょうど weekly_target 回」をハード制約にする(ADR-0003)。
    # 新規従業員は既定 True。半端な週(月末月初)は常に按分ソフト、False は常にソフト。
    weekly_shifts_pinned: bool = True
    is_dual_worker: bool = False  # True ならWワーク専用パターンにも入れる（通常従業員は基本のみ）
    # 保険区分(social/employment/none)。月間実働時間の上下限に使う(ADR-0006)。
    insurance_type: str = "none"
    # 普段入れる時間帯（1時間単位）。両方 None なら制限なし。
    available_start: int | None = None
    available_end: int | None = None


@dataclass
class AvailabilitySpec:
    employee_id: int
    target_date: date
    kind: str  # unavailable | preferred | paid_leave | mandatory(確定出勤)
    shift_type: str | None = None
    note: str | None = None  # 希望日の時間帯 "HH:MM-HH:MM"（任意）


@dataclass
class LLMConstraints:
    """Extra structured constraints returned by the LLM."""

    hard_unavailable: list[dict[str, Any]] = field(default_factory=list)
    max_shifts_per_week_override: dict[int, int] = field(default_factory=dict)
    date_notes: dict[str, str] = field(default_factory=dict)


@dataclass
class SchedulerResult:
    assignments: list[dict[str, Any]]
    solver_status: str
    solver_seconds: float
    warnings: list[str]


class ShiftScheduler:
    def __init__(
        self,
        year: int,
        month: int,
        employees: list[EmployeeSpec],
        patterns: list[PatternSpec],
        staffing_rules: dict[tuple[str, int], int],  # (day_category, hour) -> 必要人数
        availabilities: list[AvailabilitySpec],  # 従業員のシフト希望リスト
        llm_constraints: LLMConstraints | None = None,
        forbidden_pairs: list[tuple[int, int]] | None = None,  # 同時配置しない従業員の組
        max_solve_seconds: float = 20.0,
    ) -> None:
        self.year = year
        self.month = month
        self.employees = employees
        # 時間カバレッジ方式では基本/例外(Wワーク)を問わず全パターンを候補にする。
        self.patterns = list(patterns)
        self.staffing_rules = staffing_rules
        self.availabilities = availabilities
        self.llm = llm_constraints or LLMConstraints()
        self.forbidden_pairs = forbidden_pairs or []
        self.max_solve_seconds = max_solve_seconds

    def _days_in_month(self) -> list[date]:
        _, days = calendar.monthrange(self.year, self.month)
        return [date(self.year, self.month, d) for d in range(1, days + 1)]

    def _unavailable_lookup(self) -> set[tuple[int, date]]:
        s: set[tuple[int, date]] = set()
        for a in self.availabilities:
            # 勤務不可日・有給日はその日に配置しない（有給は勤務ではないため）
            if a.kind in ("unavailable", "paid_leave"):
                s.add((a.employee_id, a.target_date))
        for h in self.llm.hard_unavailable:
            try:
                eid = int(h["employee_id"])
                d = date.fromisoformat(h["date"])
                s.add((eid, d))
            except (KeyError, ValueError, TypeError):
                continue
        return s

    def _mandatory_lookup(self) -> dict[tuple[int, date], frozenset[int]]:
        # 確定出勤（ADR-0009）。その日は必ず1シフト入れる。
        # note "HH:MM-HH:MM" があれば、その時間窓に収まるパターンに限定する（1時間単位）。
        # 窓なし(空集合)ならその日の任意パターンでよい。
        out: dict[tuple[int, date], frozenset[int]] = {}
        for a in self.availabilities:
            if a.kind == "mandatory":
                out[(a.employee_id, a.target_date)] = _parse_note_hours(a.note)
        return out

    def _preferred_lookup(
        self,
    ) -> list[tuple[int, date, str | None, frozenset[int]]]:
        # (employee_id, date, shift_type, 希望時間帯の拡張時集合)。
        # 時間指定が無い希望日は空集合を持つ。
        out: list[tuple[int, date, str | None, frozenset[int]]] = []
        for a in self.availabilities:
            if a.kind == "preferred":
                out.append(
                    (a.employee_id, a.target_date, a.shift_type, _parse_note_hours(a.note))
                )
        return out

    def solve(self) -> SchedulerResult:
        """3段フォールバックで必ず部分解を返す(ADR-0003)。

        第1段: 週回数(完全週=ちょうど, ハード) ＋ 必要人数(必要〜+α, ハード) の両方で解く。
        第2段: 解が無ければ、必要人数(必要〜+α)は保ったまま週回数を目標(ソフト)に緩める。
        第3段: それでも解が無い(＝必要人数も満たせない＝真の人手不足)なら、不足を許容し警告する。
        各時間の過剰は +α まで（弱ペナルティ。ADR-0005）。α で頭打ちなので暴走はしない。
        いずれの場合も割当は返し、後から手動修正する運用を前提とする(要件書 OPT-06)。
        """
        # 第1段: 両方ハード
        p1 = self._solve_once(use_slack=False, weekly_hard=True)
        if p1.solver_status != "INFEASIBLE":
            return p1

        # 第2段: 必要人数(==)は維持し、週回数をソフトに落とす（過剰を出さない）
        p2 = self._solve_once(use_slack=False, weekly_hard=False)
        if p2.solver_status in ("OPTIMAL", "FEASIBLE"):
            p2.warnings.insert(
                0,
                "一部の従業員は希望の週回数を満たせないため、週回数を目標(ソフト)に緩めた"
                "暫定シフトを表示します（必要人数は満たしています）。"
                "対象者の週回数・勤務可能時間帯・必要人数を見直してください。",
            )
            return p2

        # 第3段: 必要人数ちょうども満たせない（真の人手不足）ため、不足を許容する
        p3 = self._solve_once(use_slack=True, weekly_hard=False)
        p3.warnings.insert(
            0,
            "各時間ちょうどの必要人数を満たす解がないため、不足を許容した暫定シフトを表示します。"
            "必要人数・シフトパターン・従業員数を見直してください。",
        )
        return p3

    # 制約をつくる
    def _solve_once(self, use_slack: bool, weekly_hard: bool) -> SchedulerResult:
        warnings: list[str] = []
        model = cp_model.CpModel()

        days = self._days_in_month()
        emps = self.employees
        pats = self.patterns
        if not emps:
            return SchedulerResult([], "NO_EMPLOYEES", 0.0, ["従業員が登録されていません"])
        if not pats:
            return SchedulerResult([], "NO_PATTERNS", 0.0, ["シフトパターンが未定義です"])

        unavailable = self._unavailable_lookup()
        preferred = self._preferred_lookup()
        # 確定出勤。勤務不可と衝突する組は勤務不可を優先して除く。
        # {(emp_id, date): 時間窓(拡張時集合。空なら任意)}
        mandatory = {
            k: v for k, v in self._mandatory_lookup().items() if k not in unavailable
        }

        # 各パターンがカバーする「拡張時」の集合を先に計算しておく（深夜跨ぎ対応）。
        pat_hours: dict[int, set[int]] = {p.id: _pattern_hours(p.start, p.end) for p in pats}

        # (day_category, hour) -> required を day_category ごとにまとめる。
        required_by_cat: dict[str, list[tuple[int, int]]] = {}
        for (dc, hour), req in self.staffing_rules.items():
            required_by_cat.setdefault(dc, []).append((hour, req))

        # x[e, d, p] = 1 if employee e is assigned pattern p on day d
        x: dict[tuple[int, date, int], cp_model.IntVar] = {}
        for e in emps:
            for d in days:
                for p in pats:
                    name = f"x_e{e.id}_d{d.isoformat()}_p{p.code}"
                    x[(e.id, d, p.id)] = model.NewBoolVar(name)

        # Constraint: each employee works at most one pattern per day
        for e in emps:
            for d in days:
                model.Add(sum(x[(e.id, d, p.id)] for p in pats) <= 1)

        # Constraint: employee cannot be assigned on unavailable days
        for e in emps:
            for d in days:
                if (e.id, d) in unavailable:
                    for p in pats:
                        model.Add(x[(e.id, d, p.id)] == 0)

        # Constraint: 確定出勤(ADR-0009)。その日は必ず1シフト入れる。時間窓(note指定)が
        # あれば、その窓に収まるパターンに限定する（1時間単位）。
        # ハード段(use_slack=False)では厳守。診断段(use_slack=True)では、物理的に不可能な
        # ときのため強いペナルティのソフトに緩め、満たせなかった分は後で警告する。
        mandatory_unmet_terms: list[cp_model.IntVar] = []
        for e in emps:
            for d in days:
                key = (e.id, d)
                if key not in mandatory:
                    continue
                hours = mandatory[key]
                # 窓ありは窓に収まるパターン、窓なしは全パターンが対象。
                eligible = [
                    x[(e.id, d, p.id)]
                    for p in pats
                    if not hours or pat_hours[p.id] <= hours
                ]
                if use_slack:
                    unmet = model.NewBoolVar(f"mand_unmet_e{e.id}_{d.isoformat()}")
                    if eligible:
                        model.Add(sum(eligible) + unmet >= 1)
                    else:
                        model.Add(unmet == 1)  # 該当パターン無し＝満たせない
                    mandatory_unmet_terms.append(unmet)
                elif eligible:
                    model.Add(sum(eligible) == 1)
                else:
                    # 窓に合うパターンが無く確定出勤を満たせない → このハード段は解なしにして
                    # 診断段へ回す（明示的な矛盾制約）。
                    imp = model.NewBoolVar(f"mand_impossible_e{e.id}_{d.isoformat()}")
                    model.Add(imp == 1)
                    model.Add(imp == 0)

        # 廃止(ADR-0002): メインシフト区分(朝/夜/深夜)による配置固定は撤廃し、
        # 配置制御は「勤務可能時間帯」(available_start/end の1時間窓ハード, 下記)に一本化した。
        # 3区分は粒度が粗く、デフォルトONにすると新規従業員が「朝」に固定される問題があったため。
        # 挙動の由来を追えるよう、旧ロジックはコメントとして残す。
        # for e in emps:
        #     if e.main_shift_pinned and e.main_shift_type:
        #         for d in days:
        #             for p in pats:
        #                 if not (p.code == e.main_shift_type or p.category == e.main_shift_type):
        #                     model.Add(x[(e.id, d, p.id)] == 0)

        # 廃止(ADR-0004): 基本/Wワークのパターン区別(is_basic)を撤廃し、全パターンを1つのプールに
        # 統合した。1時間単位の窓で配置を制御しているため区別は不要。誰でも（窓に収まる限り）
        # どのパターンにも入れる。is_dual_worker は掛け持ちの目印として残すが配置には影響しない。

        # Hard: 「普段入れる時間帯」を設定した従業員は、その窓に完全に収まる
        # パターンにしか配置しない（拡張時集合の包含で判定）。
        for e in emps:
            if e.available_start is None or e.available_end is None:
                continue
            win = _window_hours(e.available_start, e.available_end)
            for p in pats:
                if not pat_hours[p.id] <= win:
                    for d in days:
                        model.Add(x[(e.id, d, p.id)] == 0)

        # Constraint: 時間カバレッジ。各日 d・各時 h で、配置人数を「必要人数 ≤ 配置 ≤ 必要人数 + α」
        # に収める(ADR-0005)。過剰(surplus)は最大 α までハードに許し、弱ペナルティで嫌う（誰かを
        # 働かせられる時だけ +α を使う）。use_slack 時はさらに不足(shortage)も許して人手不足を診断。
        # 深夜跨ぎは拡張時(24=0:00, 25=1:00)で扱う。
        shortage_terms: list[cp_model.IntVar] = []
        surplus_terms: list[cp_model.IntVar] = []
        # (date, hour) -> (shortage, surplus)。診断(use_slack)時の警告表示に使う。
        slack_vars: dict[tuple[date, int], tuple[cp_model.IntVar, cp_model.IntVar]] = {}
        for d in days:
            day_cat = category_for(d)
            for hour, required in required_by_cat.get(day_cat, []):
                covering = [
                    x[(e.id, d, p.id)]
                    for e in emps
                    for p in pats
                    if hour in pat_hours[p.id]
                ]
                if not covering:
                    if required > 0:
                        warnings.append(
                            f"{d.isoformat()} {hour}:00台: この時間をカバーするシフトパターンが無く、"
                            f"必要人数 {required} を満たせません"
                        )
                    continue
                # 過剰は最大 α（SURPLUS_TOLERANCE）まで
                surplus = model.NewIntVar(0, SURPLUS_TOLERANCE, f"surp_{d.isoformat()}_h{hour}")
                surplus_terms.append(surplus)
                if use_slack:
                    shortage = model.NewIntVar(0, required, f"short_{d.isoformat()}_h{hour}")
                    # sum + shortage - surplus == required（不足も許容。過剰は α まで）
                    model.Add(sum(covering) + shortage - surplus == required)
                    shortage_terms.append(shortage)
                    slack_vars[(d, hour)] = (shortage, surplus)
                else:
                    # 必要人数以上・必要人数+α 以下（不足は許さない）
                    model.Add(sum(covering) - surplus == required)

        # Constraint: each employee target shifts per month = weekly_target * ~4.3 (rounded)
        max_shifts_override = {
            int(k): int(v) for k, v in self.llm.max_shifts_per_week_override.items()
        }
        # 日曜起点で週にグルーピング（採用推奨の「対応可能数」計算に使用）
        weeks: dict[date, list[date]] = {}
        for d in days:
            week_start = d - timedelta(days=(d.weekday() + 1) % 7)
            weeks.setdefault(week_start, []).append(d)

        # Constraint: 週回数の目標（日曜起点の週ごと。ADR-0003）。
        # weekly_shifts_pinned な従業員は「完全な7日週でちょうど weekly 回」をハード制約に
        # する（weekly_hard=True のときのみ。第3段フォールバックでは False で全てソフト化）。
        # 半端な週(月末月初)は常に按分ソフト、非 pinned も常にソフト。均等化は後段の balance で。
        penalties: list[cp_model.IntVar] = []
        loads: list[Any] = []
        for e in emps:
            weekly = max_shifts_override.get(e.id, e.weekly_target)
            # balance 用の月間ロードは従来どおり全日の合計で持つ
            loads.append(sum(x[(e.id, d, p.id)] for d in days for p in pats))
            for wstart, wdays in weeks.items():
                week_total = sum(x[(e.id, d, p.id)] for d in wdays for p in pats)
                is_full_week = len(wdays) == 7
                if weekly_hard and e.weekly_shifts_pinned and is_full_week:
                    # Hard: 完全週はちょうど weekly 回（絶対遵守）
                    model.Add(week_total == weekly)
                    continue
                # Soft: 目標との偏差を最小化。半端な週は日数で按分する。
                target = weekly if is_full_week else round(weekly * len(wdays) / 7)
                over = model.NewIntVar(0, len(wdays), f"over_e{e.id}_w{wstart.isoformat()}")
                under = model.NewIntVar(0, max(0, target), f"under_e{e.id}_w{wstart.isoformat()}")
                model.Add(week_total - target == over - under)
                penalties.append(over)
                penalties.append(under)

        # Constraint: 保険区分ごとの月間実働時間(分)の上下限(ADR-0006)。
        # 上限(過労側・法令準拠)は常にハード。下限(不足側)は weekly_hard の時ハード、
        # 他はソフト(不足分にペナルティ＋警告)にして週回数と同じくフォールバックで緩める。
        insurance_under_terms: list[cp_model.IntVar] = []
        total_month_minutes = sum(p.worked_minutes for p in pats) * len(days)
        for e in emps:
            lo_h, hi_h = INSURANCE_HOURS_BOUNDS.get(
                e.insurance_type, INSURANCE_HOURS_BOUNDS["none"]
            )
            worked = sum(
                x[(e.id, d, p.id)] * p.worked_minutes for d in days for p in pats
            )
            # 上限: 常にハード（雇用≤119h / なし≤79h。social は上限なし）
            if hi_h is not None:
                model.Add(worked <= hi_h * 60)
            # 下限: 0 なら制約不要
            if lo_h > 0:
                if weekly_hard:
                    model.Add(worked >= lo_h * 60)
                else:
                    # ソフト: 下限に対する不足分(分)を最小化する
                    under_min = model.NewIntVar(0, lo_h * 60, f"ins_under_e{e.id}")
                    over_min = model.NewIntVar(0, total_month_minutes, f"ins_over_e{e.id}")
                    model.Add(worked - lo_h * 60 == over_min - under_min)
                    insurance_under_terms.append(under_min)

        # Hard: 連勤制限（ADR-0008）。生成月内で連続 MAX_CONSECUTIVE_DAYS+1 日すべて勤務を禁止。
        # 各従業員・各スライディング窓で「窓内の勤務日数 ≤ MAX_CONSECUTIVE_DAYS」。
        # x は「1日1パターン以下」制約済みなので works(e,d)=Σ_p x[e,d,p] は 0/1。
        # 月をまたぐ連続は対象外（前月シフトは参照しない）。
        win = MAX_CONSECUTIVE_DAYS + 1
        if len(days) >= win:
            for e in emps:
                for i in range(len(days) - win + 1):
                    window_days = days[i : i + win]
                    model.Add(
                        sum(x[(e.id, d, p.id)] for d in window_days for p in pats)
                        <= MAX_CONSECUTIVE_DAYS
                    )

        # 人手不足チェック: 必要「シフト数」 > 対応可能「シフト数」 なら採用を推奨。
        # 必要人数は時間ごと(のべ人時)なので、平均シフト長で割って「シフト数」に換算し、
        # 従業員の対応可能シフト数(person-days)と単位を揃えて比較する。
        avg_shift_hours = max(
            1, round(sum(len(h) for h in pat_hours.values()) / len(pat_hours))
        )
        required_total = 0
        for d in days:
            day_person_hours = sum(req for _, req in required_by_cat.get(category_for(d), []))
            # 切り上げ: その日のべ人時 ÷ 平均シフト長 = 必要シフト数の目安
            required_total += (day_person_hours + avg_shift_hours - 1) // avg_shift_hours
        capacity_total = 0
        for e in emps:
            weekly_cap = max_shifts_override.get(e.id, e.weekly_target)
            for wdays in weeks.values():
                avail = sum(1 for d in wdays if (e.id, d) not in unavailable)
                capacity_total += min(weekly_cap, avail)
        if required_total > capacity_total:
            shortage_total = required_total - capacity_total
            per_new_hire = max(1, len(weeks) * DEFAULT_NEW_HIRE_WEEKLY)
            hire = (shortage_total + per_new_hire - 1) // per_new_hire
            warnings.append(
                f"人手不足の可能性: 今月の必要シフト(のべ時間) {required_total} に対し、"
                f"従業員の対応可能数は約 {capacity_total} です。"
                f"全ての時間を満たすには、あと約 {hire} 人の採用を検討してください。"
            )

        # Soft preference bonus。希望日に時間帯(note "HH:MM-HH:MM")があれば、
        # その時間とパターンのカバー時間の重なり「時間数」だけ加点する（1時間単位）。
        # 時間指定なしの希望日は従来どおりマッチ 1 件につき一律 +1。
        bonus_terms: list[Any] = []
        for eid, d, shift_type, pref_hours in preferred:
            for p in pats:
                if shift_type and p.code != shift_type and p.category != shift_type:
                    continue
                if (eid, d, p.id) not in x:
                    continue
                if pref_hours:
                    overlap = len(pref_hours & pat_hours[p.id])
                    if overlap == 0:
                        continue
                    bonus_terms.append(overlap * x[(eid, d, p.id)])
                else:
                    bonus_terms.append(x[(eid, d, p.id)])

        # ハード制約：禁止ペア（人間関係などによる）は時間帯が重なって同時勤務しない（H-6）。
        # 時間カバレッジ方式では「同じ時間に両者が居ない」= 重なり禁止 で表す
        # （非重複の別シフトなら同日でも可）。
        active_ids = {e.id for e in emps}
        all_hours = sorted(set().union(*pat_hours.values())) if pat_hours else []
        for a_id, b_id in self.forbidden_pairs:
            # 今回の対象でない従業員（退職者など）を含む組は無視する
            if a_id not in active_ids or b_id not in active_ids:
                continue
            for d in days:
                for hour in all_hours:
                    covering_pats = [p for p in pats if hour in pat_hours[p.id]]
                    if not covering_pats:
                        continue
                    model.Add(
                        sum(x[(a_id, d, p.id)] for p in covering_pats)
                        + sum(x[(b_id, d, p.id)] for p in covering_pats)
                        <= 1
                    )

        # 廃止(ADR-0002): メインシフト区分への「寄せ」ボーナスも撤廃した（配置制御は
        # 勤務可能時間帯に一本化）。挙動の由来を追えるよう、旧ロジックはコメントで残す。
        # main_shift_bonus_terms: list[cp_model.IntVar] = []
        # for e in emps:
        #     if not e.main_shift_type or e.is_dual_worker:
        #         continue
        #     for d in days:
        #         for p in pats:
        #             if p.code == e.main_shift_type or p.category == e.main_shift_type:
        #                 main_shift_bonus_terms.append(x[(e.id, d, p.id)])

        # 廃止(ADR-0004): Wワーク専用パターンへの寄せボーナスも撤廃（パターンを統合したため）。
        # dual_wwork_bonus_terms: list[cp_model.IntVar] = []
        # for e in emps:
        #     if not e.is_dual_worker:
        #         continue
        #     for d in days:
        #         for p in pats:
        #             if not p.is_basic:
        #                 dual_wwork_bonus_terms.append(x[(e.id, d, p.id)])

        # Objective: minimize deviation from monthly target and reward preferences.
        # Fairness (S-6): 勤務回数を平準化する。供給 < 需要のとき目標偏差だけでは
        # 分配が縮退して一部の従業員が 0 枠になるため、最大負荷と最小負荷の差を縮める。
        balance = 0
        if loads:
            max_load = model.NewIntVar(0, len(days), "max_load")
            min_load = model.NewIntVar(0, len(days), "min_load")
            for load_e in loads:
                model.Add(load_e <= max_load)
                model.Add(load_e >= min_load)
            balance = max_load - min_load

        obj = 0
        if penalties:
            obj += sum(penalties)
        if bonus_terms:
            obj -= PREFERENCE_WEIGHT * sum(bonus_terms)
        # 廃止(ADR-0002): メインシフト寄せボーナスは objective から除外。
        # if main_shift_bonus_terms:
        #     obj -= MAIN_SHIFT_WEIGHT * sum(main_shift_bonus_terms)
        # 廃止(ADR-0004): Wワーク寄せボーナスは objective から除外。
        # if dual_wwork_bonus_terms:
        #     obj -= DUAL_WWORK_WEIGHT * sum(dual_wwork_bonus_terms)
        if loads:
            obj += BALANCE_WEIGHT * balance
        if shortage_terms:
            # 不足は他のどの目的より優先して潰す（十分大きな重み）。
            obj += COVERAGE_SLACK_WEIGHT * sum(shortage_terms)
        if surplus_terms:
            # 過剰(最大α)は弱く嫌う。誰かを働かせられる時だけ +α を使い、無駄な過剰は出さない。
            obj += SURPLUS_WEIGHT * sum(surplus_terms)
        if insurance_under_terms:
            # 保険区分の下限に対する不足(分)を弱く嫌う（下限がソフトの段のみ）。
            obj += INSURANCE_UNDER_WEIGHT * sum(insurance_under_terms)
        if mandatory_unmet_terms:
            # 確定出勤の未達は強く嫌う（不足の次に優先。診断段のみ）。
            obj += MANDATORY_WEIGHT * sum(mandatory_unmet_terms)
        model.Minimize(obj)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.max_solve_seconds
        solver.parameters.num_search_workers = 4
        started = _time.time()
        status = solver.Solve(model)
        elapsed = _time.time() - started

        status_str = solver.StatusName(status)
        assignments: list[dict[str, Any]] = []
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            worked_min_by_emp: dict[int, int] = {}
            for e in emps:
                for d in days:
                    for p in pats:
                        if solver.Value(x[(e.id, d, p.id)]) == 1:
                            crosses = _crosses_midnight(p.start, p.end)
                            worked_min_by_emp[e.id] = (
                                worked_min_by_emp.get(e.id, 0) + p.worked_minutes
                            )
                            assignments.append(
                                {
                                    "employee_id": e.id,
                                    "target_date": d,
                                    "shift_type": p.code,
                                    "start_time": p.start,
                                    "end_time": p.end,
                                    "crosses_midnight": crosses,
                                    "rest_minutes": p.rest_minutes,
                                }
                            )
            if use_slack:
                warnings.extend(self._slack_warnings(solver, slack_vars))
            # 確定出勤を満たせなかった (従業員, 日) を警告(診断段でのみ起こる)。
            # 窓ありは「窓に収まるパターンで働いたか」まで確認する。
            if mandatory:
                pat_hours_by_code = {p.code: pat_hours[p.id] for p in pats}
                assigned_hours = {
                    (a["employee_id"], a["target_date"]): pat_hours_by_code[a["shift_type"]]
                    for a in assignments
                }
                unmet = []
                for key, hours in mandatory.items():
                    ah = assigned_hours.get(key)
                    if ah is None or (hours and not ah <= hours):
                        unmet.append(key)
                unmet.sort()
                if unmet:
                    names = {e.id: e.name for e in emps}
                    examples = "、".join(
                        f"{names.get(eid, eid)} {d.isoformat()}" for eid, d in unmet[:3]
                    )
                    more = f" ほか{len(unmet) - 3}件" if len(unmet) > 3 else ""
                    warnings.append(
                        f"確定出勤を満たせませんでした: {len(unmet)}件（例: {examples}{more}）。"
                        f"勤務可能時間帯・必要人数・連勤/保険の制約を見直してください。"
                    )
            # 保険区分の下限を満たせなかった従業員を警告(下限をソフトに緩めた段でのみ起こる)。
            for e in emps:
                lo_h, _ = INSURANCE_HOURS_BOUNDS.get(
                    e.insurance_type, INSURANCE_HOURS_BOUNDS["none"]
                )
                if lo_h > 0 and worked_min_by_emp.get(e.id, 0) < lo_h * 60:
                    got_h = worked_min_by_emp.get(e.id, 0) / 60
                    warnings.append(
                        f"{e.name} は保険区分({e.insurance_type})の月間下限 {lo_h}h に達していません"
                        f"（実働 約{got_h:.1f}h）。勤務可能時間帯・必要人数・保険区分を見直してください。"
                    )
        else:
            warnings.append(
                f"CP-SAT が解を見つけられませんでした ({status_str})。必要人数や制約を緩めてください。"
            )

        return SchedulerResult(
            assignments=assignments,
            solver_status=status_str,
            solver_seconds=round(elapsed, 3),
            warnings=warnings,
        )

    @staticmethod
    def _slack_warnings(
        solver: cp_model.CpSolver,
        slack_vars: dict[tuple[date, int], tuple[cp_model.IntVar, cp_model.IntVar]],
    ) -> list[str]:
        """診断ソルブの結果から、必要人数を満たせなかった時間帯を要約する。"""
        shortages: list[tuple[date, int, int]] = []
        surpluses: list[tuple[date, int, int]] = []
        for (d, hour), (sh, su) in slack_vars.items():
            s = int(solver.Value(sh))
            o = int(solver.Value(su))
            if s > 0:
                shortages.append((d, hour, s))
            if o > 0:
                surpluses.append((d, hour, o))

        warnings: list[str] = []
        for label, items in (("不足", shortages), ("過剰", surpluses)):
            if not items:
                continue
            items.sort()
            examples = "、".join(
                f"{d.isoformat()} {hour}:00台 {n}人" for d, hour, n in items[:3]
            )
            more = f" ほか{len(items) - 3}件" if len(items) > 3 else ""
            warnings.append(f"必要人数{label}: {len(items)} 時間帯（例: {examples}{more}）")
        return warnings


def _crosses_midnight(start: time, end: time) -> bool:
    return end <= start


def worked_minutes_of(start: time, end: time, rest_minutes: int) -> int:
    """パターンの実働(分) = スパン(分) − 休憩(分)。深夜跨ぎは終了に +24h する。

    保険区分の月間実働時間制約(ADR-0006)に使う。分単位で厳密に扱う。
    """
    start_min = start.hour * 60 + start.minute
    end_min = end.hour * 60 + end.minute
    if end_min <= start_min:  # 深夜跨ぎ（例 17:00-1:00）
        end_min += 24 * 60
    return max(0, end_min - start_min - rest_minutes)


def _window_hours(start: int, end: int) -> set[int]:
    """「普段入れる時間帯」を拡張時集合に変換（_pattern_hours と同じ規約）。

    例: 9-22 -> {9..21} / 18-2（翌2:00）-> {18..25}。パターンのカバー時間が
    この集合に完全に含まれるときだけ配置可とする。
    """
    if end <= start:
        end += 24
    return set(range(start, end))


def _parse_note_hours(note: str | None) -> frozenset[int]:
    """希望日メモ "HH:MM-HH:MM" を拡張時集合に変換する（_pattern_hours と同じ規約）。

    解釈できない書式や時間指定なしのときは空集合を返す。
    例: "09:00-17:00" -> {9..16} / "20:00-01:00" -> {20..24}（深夜跨ぎ）。
    分は切り捨て（時間粒度で扱う）。
    """
    if not note:
        return frozenset()
    try:
        start_s, end_s = note.split("-")
        s = int(start_s.split(":")[0])
        e = int(end_s.split(":")[0])
    except (ValueError, IndexError):
        return frozenset()
    if not (0 <= s <= 24 and 0 <= e <= 24):
        return frozenset()
    if e <= s:  # 深夜跨ぎ（例 20:00-01:00）は翌日側を +24 する
        e += 24
    return frozenset(range(s, e))


def _pattern_hours(start: time, end: time) -> set[int]:
    """パターンがカバーする「拡張時」の集合を返す。

    営業日は 1:00 起点で扱い、深夜跨ぎは拡張時(24=翌0:00, 25=翌1:00)で表す。
    例: 深夜 1:00-9:00 -> {1..8} / 朝 9:00-17:00 -> {9..16} /
        夜 17:00-1:00 -> {17..24} / Wワーク 20:00-1:00 -> {20..24}。
    分は切り捨て（時間粒度で扱う）。
    """
    s = start.hour
    e = end.hour
    if e <= s:  # 深夜跨ぎ（例 17:00-1:00）は翌日側を +24 する
        e += 24
    return set(range(s, e))
