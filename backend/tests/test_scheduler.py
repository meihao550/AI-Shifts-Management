"""ShiftScheduler の禁止ペア（ハード制約 H-6）に関するテスト。

「制約が効いているか」は、わざと破れない状況を作って INFEASIBLE になるか、
逆に分けられる状況では同居しないか、で確認する。
"""

from datetime import time

from app.services.scheduler import EmployeeSpec, PatternSpec, ShiftScheduler


def _employee(emp_id: int, name: str) -> EmployeeSpec:
    return EmployeeSpec(
        id=emp_id,
        name=name,
        weekly_target=7,
        main_shift_type=None,
        hourly_wage=1000,
    )


def _pattern(pattern_id: int, code: str, category: str, start: time, end: time) -> PatternSpec:
    return PatternSpec(
        id=pattern_id,
        code=code,
        label=code,
        start=start,
        end=end,
        category=category,
        is_basic=True,
    )


MORNING = _pattern(1, "morning", "morning", time(9, 0), time(17, 0))
EVENING = _pattern(2, "evening", "evening", time(17, 0), time(1, 0))


def _make_scheduler(
    patterns: list[PatternSpec],
    staffing_rules: dict[tuple[str, str], int],
    forbidden_pairs: list[tuple[int, int]] | None = None,
) -> ShiftScheduler:
    return ShiftScheduler(
        year=2026,
        month=2,
        employees=[_employee(1, "A"), _employee(2, "B")],
        patterns=patterns,
        staffing_rules=staffing_rules,
        availabilities=[],
        forbidden_pairs=forbidden_pairs,
        max_solve_seconds=10.0,
    )


def test_feasible_without_forbidden_pair():
    """対照: 禁止ペアなしなら「朝2人」ルールは解ける。"""
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules={("weekday", "morning"): 2, ("weekend_or_holiday", "morning"): 2},
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")


def test_forbidden_pair_makes_infeasible():
    """従業員が2人だけ・朝2人必須なのに、その2人が禁止ペア → 解なし。"""
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules={("weekday", "morning"): 2, ("weekend_or_holiday", "morning"): 2},
        forbidden_pairs=[(1, 2)],
    ).solve()
    assert result.solver_status == "INFEASIBLE"


def test_forbidden_pair_are_separated_when_possible():
    """朝1・夜1なら、禁止ペアでも別区分に分けて解ける。同じ日・同じ区分には同居しない。"""
    result = _make_scheduler(
        patterns=[MORNING, EVENING],
        staffing_rules={
            ("weekday", "morning"): 1,
            ("weekday", "evening"): 1,
            ("weekend_or_holiday", "morning"): 1,
            ("weekend_or_holiday", "evening"): 1,
        },
        forbidden_pairs=[(1, 2)],
    ).solve()

    assert result.solver_status in ("OPTIMAL", "FEASIBLE")

    # 同じ (日付, 区分) に 1番と2番が同居していないことを確認する
    code_to_category = {MORNING.code: MORNING.category, EVENING.code: EVENING.category}
    slot_members: dict[tuple[object, str], set[int]] = {}
    for a in result.assignments:
        slot = (a["target_date"], code_to_category[a["shift_type"]])
        slot_members.setdefault(slot, set()).add(a["employee_id"])
    for members in slot_members.values():
        assert not ({1, 2} <= members)


def test_load_is_balanced_across_employees():
    """供給が少なくても勤務は公平に分配され、一部の従業員が 0 枠にならない。"""
    employees = [_employee(i, f"E{i}") for i in range(1, 6)]  # 5 人
    scheduler = ShiftScheduler(
        year=2026,
        month=2,
        employees=employees,
        patterns=[MORNING],
        staffing_rules={("weekday", "morning"): 1, ("weekend_or_holiday", "morning"): 1},
        availabilities=[],
        max_solve_seconds=10.0,
    )
    result = scheduler.solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")

    counts = {e.id: 0 for e in employees}
    for a in result.assignments:
        counts[a["employee_id"]] += 1
    values = list(counts.values())
    assert min(values) >= 1  # 誰も 0 枠にならない
    assert max(values) - min(values) <= 2  # 偏りが小さい
