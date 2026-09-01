"""ShiftScheduler（時間カバレッジ方式）のテスト。

必要人数は「1時間ごと」に持ち、各時間ちょうど(==)を満たすことを確認する。
満たせない場合はスラック付き診断ソルブで不足時間帯を warning に出す。
"""

from datetime import time

from app.services.scheduler import (
    EmployeeSpec,
    PatternSpec,
    ShiftScheduler,
    _pattern_hours,
)


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

MORNING_HOURS = range(9, 17)  # 9:00-17:00
EVENING_HOURS = range(17, 25)  # 17:00-翌1:00（拡張時）


def _hourly(*specs: tuple[range, int]) -> dict[tuple[str, int], int]:
    """(時間レンジ, 必要人数) から (day_category, hour)->required を作る（平日=土日祝）。"""
    rules: dict[tuple[str, int], int] = {}
    for hours, required in specs:
        for h in hours:
            rules[("weekday", h)] = required
            rules[("weekend_or_holiday", h)] = required
    return rules


def _make_scheduler(
    patterns: list[PatternSpec],
    staffing_rules: dict[tuple[str, int], int],
    employees: list[EmployeeSpec] | None = None,
    forbidden_pairs: list[tuple[int, int]] | None = None,
) -> ShiftScheduler:
    return ShiftScheduler(
        year=2026,
        month=2,
        employees=employees or [_employee(1, "A"), _employee(2, "B")],
        patterns=patterns,
        staffing_rules=staffing_rules,
        availabilities=[],
        forbidden_pairs=forbidden_pairs,
        max_solve_seconds=10.0,
    )


# ---- _pattern_hours の単体テスト -------------------------------------------------


def test_pattern_hours_basic():
    assert _pattern_hours(time(9, 0), time(17, 0)) == set(range(9, 17))
    assert _pattern_hours(time(1, 0), time(9, 0)) == set(range(1, 9))


def test_pattern_hours_crosses_midnight():
    # 17:00-1:00 は拡張時で 17..24（24=翌0:00 台）
    assert _pattern_hours(time(17, 0), time(1, 0)) == set(range(17, 25))
    # Wワーク 20:00-1:00 は 20..24
    assert _pattern_hours(time(20, 0), time(1, 0)) == set(range(20, 25))


# ---- カバレッジ制約（==） -------------------------------------------------------


def test_each_hour_meets_required_exactly():
    """朝の各時間に 2 人必要 → 2 人が朝に入り、各時間ちょうど 2 人になる。"""
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 2)),
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")

    # 各 (日付, 時間) のカバレッジがちょうど 2 であること
    coverage: dict[tuple[object, int], int] = {}
    for a in result.assignments:
        for h in _pattern_hours(a["start_time"], a["end_time"]):
            coverage[(a["target_date"], h)] = coverage.get((a["target_date"], h), 0) + 1
    for (_, h), n in coverage.items():
        if h in MORNING_HOURS:
            assert n == 2


def test_infeasible_reports_shortage_via_slack():
    """朝に 2 人必要なのに従業員が 1 人 → 厳密解なし。暫定解＋不足 warning を返す。"""
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 2)),
        employees=[_employee(1, "A")],
    ).solve()
    # スラック診断で暫定解が返る（INFEASIBLE のままにしない）
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert any("暫定" in w for w in result.warnings)
    assert any("不足" in w for w in result.warnings)


# ---- 禁止ペア（H-6, 時間重なり禁止） -------------------------------------------


def test_forbidden_pair_separated_into_non_overlapping_shifts():
    """朝1・夜1なら、禁止ペアでも重ならない別シフトに分けて解ける。"""
    result = _make_scheduler(
        patterns=[MORNING, EVENING],
        staffing_rules=_hourly((MORNING_HOURS, 1), (EVENING_HOURS, 1)),
        forbidden_pairs=[(1, 2)],
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert not any("不足" in w for w in result.warnings)

    # 同じ日に、重なる時間帯で 1番と2番が同居していないこと
    per_day_hours: dict[tuple[object, int], set[int]] = {}
    for a in result.assignments:
        for h in _pattern_hours(a["start_time"], a["end_time"]):
            per_day_hours.setdefault((a["target_date"], h), set()).add(a["employee_id"])
    for members in per_day_hours.values():
        assert not ({1, 2} <= members)


def test_forbidden_pair_causes_shortage_when_both_needed_same_hour():
    """朝2人必須なのに従業員2人が禁止ペア → 各朝時間を満たせず不足 warning。"""
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 2)),
        forbidden_pairs=[(1, 2)],
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert any("不足" in w for w in result.warnings)


# ---- 平準化・ピン・採用推奨 -----------------------------------------------------


def test_load_is_balanced_across_employees():
    """供給が少なくても勤務は公平に分配され、一部の従業員が 0 枠にならない。"""
    employees = [_employee(i, f"E{i}") for i in range(1, 6)]  # 5 人
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 1)),
        employees=employees,
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")

    counts = {e.id: 0 for e in employees}
    for a in result.assignments:
        counts[a["employee_id"]] += 1
    values = list(counts.values())
    assert min(values) >= 1  # 誰も 0 枠にならない
    assert max(values) - min(values) <= 2  # 偏りが小さい


def test_pinned_employee_only_gets_main_category():
    """メイン固定(ピン)した従業員は、メイン区分以外には配置されない（絶対遵守）。"""
    a = EmployeeSpec(
        id=1,
        name="A",
        weekly_target=7,
        main_shift_type="morning",
        hourly_wage=1000,
        main_shift_pinned=True,
    )
    b = EmployeeSpec(id=2, name="B", weekly_target=7, main_shift_type=None, hourly_wage=1000)
    result = _make_scheduler(
        patterns=[MORNING, EVENING],
        staffing_rules=_hourly((MORNING_HOURS, 1), (EVENING_HOURS, 1)),
        employees=[a, b],
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")

    code_to_category = {MORNING.code: MORNING.category, EVENING.code: EVENING.category}
    for asg in result.assignments:
        if asg["employee_id"] == 1:  # ピンした A はメイン区分(morning)のみ
            assert code_to_category[asg["shift_type"]] == "morning"


def test_staffing_shortage_recommends_hiring():
    """必要人数に対し従業員が足りないとき、採用を促す警告が出る。"""
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 2)),
        employees=[_employee(1, "A")],  # 1 人だけ
    ).solve()
    assert any("採用" in w for w in result.warnings)
