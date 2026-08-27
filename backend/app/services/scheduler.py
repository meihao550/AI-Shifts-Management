"""CP-SAT shift scheduler.

Given
  - month (year, month)
  - employees + weekly desired shift count
  - shift patterns (basic + exception)
  - staffing rules (weekday/weekend-holiday × morning/evening/night)
  - availability (unavailable / preferred)
  - LLM-derived constraints (optional)

Produce a monthly assignment that:
  * meets required staffing per (date, shift_category) — HARD
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
        staffing_rules: dict[tuple[str, str], int],
        availabilities: list[AvailabilitySpec],  # 従業員のシフト希望リスト
        llm_constraints: LLMConstraints | None = None,
        forbidden_pairs: list[tuple[int, int]] | None = None,  # 同時配置しない従業員の組
        max_solve_seconds: float = 20.0,
    ) -> None:
        self.year = year
        self.month = month
        self.employees = employees
        self.patterns = [p for p in patterns if p.is_basic]  # scheduler uses only basic patterns
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
            if a.kind == "unavailable":
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

    # 制約をつくる
    def solve(self) -> SchedulerResult:
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

        # Constraint: required staffing per (date, shift_category)
        for d in days:
            day_cat = category_for(d)
            for shift_cat in ("morning", "evening", "night"):
                required = self.staffing_rules.get((day_cat, shift_cat), 0)
                pats_in_cat = [p for p in pats if p.category == shift_cat]
                if not pats_in_cat:
                    if required > 0:
                        warnings.append(
                            f"{d.isoformat()}: {shift_cat} パターンが定義されておらず必要人数を満たせません"
                        )
                    continue
                total = sum(x[(e.id, d, p.id)] for e in emps for p in pats_in_cat)
                model.Add(total == required)

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

        # 人手不足チェック: 必要シフト総数 > 従業員の対応可能総数 なら採用を推奨
        required_total = sum(
            self.staffing_rules.get((category_for(d), cat), 0)
            for d in days
            for cat in ("morning", "evening", "night")
        )
        capacity_total = 0
        for e in emps:
            weekly_cap = max_shifts_override.get(e.id, e.weekly_target)
            for wdays in weeks.values():
                avail = sum(1 for d in wdays if (e.id, d) not in unavailable)
                capacity_total += min(weekly_cap, avail)
        if required_total > capacity_total:
            shortage = required_total - capacity_total
            per_new_hire = max(1, len(weeks) * DEFAULT_NEW_HIRE_WEEKLY)
            hire = (shortage + per_new_hire - 1) // per_new_hire
            warnings.append(
                f"人手不足の可能性: 今月の必要シフト {required_total} 件に対し、"
                f"従業員の対応可能数は約 {capacity_total} 件です。"
                f"全ての枠を満たすには、あと約 {hire} 人の採用を検討してください。"
            )

        # Soft preference bonus
        bonus_terms = []
        for eid, d, shift_type in preferred:
            for p in pats:
                if shift_type and p.code != shift_type and p.category != shift_type:
                    continue
                if (eid, d, p.id) in x:
                    bonus_terms.append(x[(eid, d, p.id)])

        # ハード制約：禁止ペア（人間関係などによる）は同じ日・同じ区分に同時配置しない（H-6）
        active_ids = {e.id for e in emps}
        for a_id, b_id in self.forbidden_pairs:
            # 今回の対象でない従業員（退職者など）を含む組は無視する
            if a_id not in active_ids or b_id not in active_ids:
                continue
            for d in days:
                for cat in ("morning", "evening", "night"):
                    pats_c = [p for p in pats if p.category == cat]
                    if not pats_c:
                        continue
                    # a と b がこの区分に入る数の合計は最大 1（= 2 人同時は不可）
                    model.Add(
                        sum(x[(a_id, d, p.id)] for p in pats_c)
                        + sum(x[(b_id, d, p.id)] for p in pats_c)
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

        # Objective: minimize deviation from weekly target, reward preferences and main_shift matches.
        # main_shift の重みは preference より強く (weight=5) して、可能な限り希望シフトに近づける。
        # Fairness (S-6): 勤務時間を平準化する。供給 < 需要のとき目標偏差だけでは
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


def _crosses_midnight(start: time, end: time) -> bool:
    return end <= start
