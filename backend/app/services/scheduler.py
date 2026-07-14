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
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, time
from typing import Any

from ortools.sat.python import cp_model

from app.services.holidays import category_for


@dataclass(frozen=True)
class PatternSpec:
    id: int
    code: str
    label: str
    start: time
    end: time
    category: str  # morning|evening|night
    is_basic: bool


@dataclass(frozen=True)
class EmployeeSpec:
    id: int
    name: str
    weekly_target: int
    main_shift_type: str | None
    hourly_wage: int


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
        availabilities: list[AvailabilitySpec],
        llm_constraints: LLMConstraints | None = None,
        max_solve_seconds: float = 20.0,
    ) -> None:
        self.year = year
        self.month = month
        self.employees = employees
        self.patterns = [p for p in patterns if p.is_basic]  # scheduler uses only basic patterns
        self.staffing_rules = staffing_rules
        self.availabilities = availabilities
        self.llm = llm_constraints or LLMConstraints()
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
        penalties: list[cp_model.IntVar] = []
        for e in emps:
            weekly = max_shifts_override.get(e.id, e.weekly_target)
            monthly_target = max(
                0, weekly * (len(days) // 7 + (1 if len(days) % 7 else 0))
            )
            total = sum(x[(e.id, d, p.id)] for d in days for p in pats)
            over = model.NewIntVar(0, len(days), f"over_e{e.id}")
            under = model.NewIntVar(0, len(days), f"under_e{e.id}")
            model.Add(total - monthly_target == over - under)
            penalties.append(over)
            penalties.append(under)

        # Soft preference bonus
        bonus_terms = []
        for eid, d, shift_type in preferred:
            for p in pats:
                if shift_type and p.code != shift_type and p.category != shift_type:
                    continue
                if (eid, d, p.id) in x:
                    bonus_terms.append(x[(eid, d, p.id)])

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
        obj = 0
        if penalties:
            obj += sum(penalties)
        if bonus_terms:
            obj -= 3 * sum(bonus_terms)
        if main_shift_bonus_terms:
            obj -= 5 * sum(main_shift_bonus_terms)
        if penalties or bonus_terms or main_shift_bonus_terms:
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
