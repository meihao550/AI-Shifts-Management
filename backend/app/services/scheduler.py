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
  * respects each employee's weekly shift target — SOFT
  * balances load — SOFT
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
MAIN_SHIFT_WEIGHT = 1
# 新規採用者の想定 週勤務回数（人手不足時の推奨採用人数の計算に使用）
DEFAULT_NEW_HIRE_WEEKLY = 5
# 時間カバレッジ違反（不足/過剰）のペナルティ重み。他のどの目的より十分大きくして、
# 「厳密解が存在するなら必ず各時間ちょうどを満たす」ようにする（診断用の暫定解でのみ使用）。
COVERAGE_SLACK_WEIGHT = 1000


@dataclass(frozen=True)
class PatternSpec:
    id: int
    code: str  # 内部の名前
    label: str  # 表示名
    start: time  # 開始時刻
    end: time  # 終了時刻
    category: str  # morning|evening|night
    is_basic: bool  # 基本パターンかどうか


@dataclass(frozen=True)
class EmployeeSpec:
    id: int
    name: str
    weekly_target: int  # 週に何回入りたいか
    main_shift_type: str | None  # メインのシフト: Noneの場合もある
    hourly_wage: int
    main_shift_pinned: bool = False  # True ならメイン区分のみに配置(ハード制約)
    is_dual_worker: bool = False  # True ならWワーク専用パターンにも入れる（通常従業員は基本のみ）


@dataclass
class AvailabilitySpec:
    employee_id: int
    target_date: date
    kind: str  # unavailable | preferred
    shift_type: str | None = None


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

    def _preferred_lookup(self) -> set[tuple[int, date, str | None]]:
        s: set[tuple[int, date, str | None]] = set()
        for a in self.availabilities:
            if a.kind == "preferred":
                s.add((a.employee_id, a.target_date, a.shift_type))
        return s

    def solve(self) -> SchedulerResult:
        """まず「各時間ちょうど(==)」のハード制約で解く。

        解が無い(INFEASIBLE)場合は、時間カバレッジをスラック(不足/過剰)付きに緩めて
        再ソルブし、どの時間帯が満たせないかを診断しつつ暫定シフトを返す(要件書 OPT-06)。
        """
        hard = self._solve_once(use_slack=False)
        if hard.solver_status != "INFEASIBLE":
            return hard

        diag = self._solve_once(use_slack=True)
        diag.warnings.insert(
            0,
            "各時間ちょうどの必要人数を満たす解がないため、不足を許容した暫定シフトを表示します。"
            "必要人数・シフトパターン・希望を見直してください。",
        )
        return diag

    # 制約をつくる
    def _solve_once(self, use_slack: bool) -> SchedulerResult:
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

        # Hard: メインシフトをピン留めした従業員は、メイン区分以外に配置しない（絶対遵守）
        for e in emps:
            if e.main_shift_pinned and e.main_shift_type:
                for d in days:
                    for p in pats:
                        if not (p.code == e.main_shift_type or p.category == e.main_shift_type):
                            model.Add(x[(e.id, d, p.id)] == 0)

        # Hard: Wワーク専用パターン(is_basic=False)は、Wワーク従業員のみに配置する。
        # 通常従業員(is_dual_worker=False)はWワーク専用パターンには入れない。
        for e in emps:
            if e.is_dual_worker:
                continue
            for d in days:
                for p in pats:
                    if not p.is_basic:
                        model.Add(x[(e.id, d, p.id)] == 0)

        # Constraint: 時間カバレッジ。各日 d・各時 h で、その時間をカバーするパターンに
        # 入っている人数の合計 == 必要人数。深夜跨ぎは拡張時(24=0:00, 25=1:00)で扱う。
        slack_terms: list[cp_model.IntVar] = []
        # (date, hour) -> (shortage, surplus)。診断(use_slack)時のみ。
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
                if use_slack:
                    shortage = model.NewIntVar(0, required, f"short_{d.isoformat()}_h{hour}")
                    surplus = model.NewIntVar(0, len(emps), f"surp_{d.isoformat()}_h{hour}")
                    # sum + shortage - surplus == required（不足も過剰も許容し、後で最小化）
                    model.Add(sum(covering) + shortage - surplus == required)
                    slack_vars[(d, hour)] = (shortage, surplus)
                    slack_terms.append(shortage)
                    slack_terms.append(surplus)
                else:
                    model.Add(sum(covering) == required)

        # Constraint: each employee target shifts per month = weekly_target * ~4.3 (rounded)
        max_shifts_override = {
            int(k): int(v) for k, v in self.llm.max_shifts_per_week_override.items()
        }
        # 日曜起点で週にグルーピング（採用推奨の「対応可能数」計算に使用）
        weeks: dict[date, list[date]] = {}
        for d in days:
            week_start = d - timedelta(days=(d.weekday() + 1) % 7)
            weeks.setdefault(week_start, []).append(d)

        # Constraint: 月間の目標(週回数×週数)に近づける(ソフト)。分配の均等化は後段の balance で。
        penalties: list[cp_model.IntVar] = []
        loads: list[Any] = []
        for e in emps:
            weekly = max_shifts_override.get(e.id, e.weekly_target)
            monthly_target = max(0, weekly * (len(days) // 7 + (1 if len(days) % 7 else 0)))
            total = sum(x[(e.id, d, p.id)] for d in days for p in pats)
            loads.append(total)
            over = model.NewIntVar(0, len(days), f"over_e{e.id}")
            under = model.NewIntVar(0, monthly_target, f"under_e{e.id}")
            model.Add(total - monthly_target == over - under)
            penalties.append(over)
            penalties.append(under)

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

        # Soft preference bonus
        bonus_terms = []
        for eid, d, shift_type in preferred:
            for p in pats:
                if shift_type and p.code != shift_type and p.category != shift_type:
                    continue
                if (eid, d, p.id) in x:
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

        # Soft main_shift_type bonus:
        # 各従業員は自身の main_shift_type と一致するシフトを優先して割り当てたい。
        # 一致した割当 1 個ごとに +1 のボーナス。
        main_shift_bonus_terms: list[cp_model.IntVar] = []
        for e in emps:
            if not e.main_shift_type:
                continue
            for d in days:
                for p in pats:
                    if p.code == e.main_shift_type or p.category == e.main_shift_type:
                        main_shift_bonus_terms.append(x[(e.id, d, p.id)])

        # Objective: minimize deviation from monthly target, reward preferences and main_shift matches.
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
        if main_shift_bonus_terms:
            obj -= MAIN_SHIFT_WEIGHT * sum(main_shift_bonus_terms)
        if loads:
            obj += BALANCE_WEIGHT * balance
        if slack_terms:
            # カバレッジ違反は他のどの目的より優先して潰す（十分大きな重み）。
            obj += COVERAGE_SLACK_WEIGHT * sum(slack_terms)
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
            for e in emps:
                for d in days:
                    for p in pats:
                        if solver.Value(x[(e.id, d, p.id)]) == 1:
                            crosses = _crosses_midnight(p.start, p.end)
                            assignments.append(
                                {
                                    "employee_id": e.id,
                                    "target_date": d,
                                    "shift_type": p.code,
                                    "start_time": p.start,
                                    "end_time": p.end,
                                    "crosses_midnight": crosses,
                                }
                            )
            if use_slack:
                warnings.extend(self._slack_warnings(solver, slack_vars))
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
