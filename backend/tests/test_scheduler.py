"""ShiftScheduler（時間カバレッジ方式）のテスト。

必要人数は「1時間ごと」に持ち、各時間ちょうど(==)を満たすことを確認する。
満たせない場合はスラック付き診断ソルブで不足時間帯を warning に出す。
"""

from collections import defaultdict
from datetime import date as _date
from datetime import time, timedelta

from app.services.scheduler import (
    EmployeeSpec,
    PatternSpec,
    ShiftScheduler,
    _pattern_hours,
)


def _employee(emp_id: int, name: str) -> EmployeeSpec:
    # 週回数固定は既定 OFF にして、カバレッジ/平準化など各テストの主眼を邪魔しないようにする。
    return EmployeeSpec(
        id=emp_id,
        name=name,
        weekly_target=7,
        hourly_wage=1000,
        weekly_shifts_pinned=False,
    )


def _pattern(pattern_id: int, code: str, category: str, start: time, end: time) -> PatternSpec:
    return PatternSpec(
        id=pattern_id,
        code=code,
        label=code,
        start=start,
        end=end,
        category=category,
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
    """朝1・夜1なら、禁止ペアでも重ならない別シフトに分けて解ける。

    連勤制限(最大4連勤, ADR-0008)があるため、毎日 朝1+夜1 を満たすには2人では足りない
    （各人が週1日は休む）。十分な人数を与えたうえで、禁止ペア(1,2)が同時間帯に同居しない
    ことを検証する。
    """
    result = _make_scheduler(
        patterns=[MORNING, EVENING],
        staffing_rules=_hourly((MORNING_HOURS, 1), (EVENING_HOURS, 1)),
        employees=[_employee(i, f"E{i}") for i in range(1, 5)],
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


def test_weekly_pinned_exact_when_feasible():
    """需要と週回数が両立するとき、pinned 従業員は完全週でちょうど weekly_target 回入る。

    2026年2月は日曜始まりの完全4週。7人×週1回で、朝は毎日1人 → 各人ちょうど週1回で
    全日を過不足なくカバーできる（第1段で両方ハードが解ける）。
    """
    emps = [
        EmployeeSpec(
            id=i, name=f"E{i}", weekly_target=1, hourly_wage=1000, weekly_shifts_pinned=True
        )
        for i in range(1, 8)
    ]
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 1)),
        employees=emps,
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert not any("不足" in w for w in result.warnings)

    # 各週(日曜起点)・各人ちょうど1回
    per_week: dict[tuple[int, object], int] = defaultdict(int)
    for a in result.assignments:
        d = a["target_date"]
        week_start = d - timedelta(days=(d.weekday() + 1) % 7)
        per_week[(a["employee_id"], week_start)] += 1
    assert per_week
    assert all(c == 1 for c in per_week.values())


def test_overstaffing_capped_at_alpha(monkeypatch):
    """供給過多でも過剰配置は各時間「必要人数 + α」で頭打ちになる（ADR-0005）。

    3人が全員「週7回(毎日)」固定だが、朝は毎日1人しか要らない。α=1 なので各時間は
    最大2人まで。以前の「1枠に殺到」のような暴走は起きない。週回数(ちょうど7)は
    満たせないのでその旨を警告する。
    """
    from app.services import scheduler as sched

    monkeypatch.setattr(sched, "SURPLUS_TOLERANCE", 1)
    emps = [
        EmployeeSpec(
            id=i, name=f"E{i}", weekly_target=7, hourly_wage=1000, weekly_shifts_pinned=True
        )
        for i in range(1, 4)
    ]
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 1)),
        employees=emps,
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")

    # どの(日,時)も必要人数(1) + α(1) = 2 を超えない
    coverage: dict[tuple[object, int], int] = defaultdict(int)
    for a in result.assignments:
        for h in _pattern_hours(a["start_time"], a["end_time"]):
            coverage[(a["target_date"], h)] += 1
    assert coverage
    assert all(n <= 2 for n in coverage.values())
    # 週回数(ちょうど7)は満たせないので警告が出る
    assert any("週回数" in w for w in result.warnings)


def test_any_employee_can_use_any_pattern():
    """パターン統合(ADR-0004): 基本/Wワークの区別が無くなり、通常従業員でも
    どのパターンにも入れる（配置制限は勤務可能時間帯のみ）。"""
    late = PatternSpec(
        id=3,
        code="w_20_01",
        label="20:00-01:00",
        start=time(20, 0),
        end=time(1, 0),
        category="evening",
    )
    normal = EmployeeSpec(
        id=1, name="通常", weekly_target=7, hourly_wage=1000, weekly_shifts_pinned=False
    )
    # 20-24時台に1人必要。以前は「Wワーク専用」で通常従業員は入れなかったが、今は入れる。
    result = _make_scheduler(
        patterns=[MORNING, late],
        staffing_rules=_hourly((range(20, 25), 1)),
        employees=[normal],
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert any(a["shift_type"] == "w_20_01" for a in result.assignments)


def test_staffing_shortage_recommends_hiring():
    """必要人数に対し従業員が足りないとき、採用を促す警告が出る。"""
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 2)),
        employees=[_employee(1, "A")],  # 1 人だけ
    ).solve()
    assert any("採用" in w for w in result.warnings)


# ---- 「普段入れる時間帯」ハード制約 ---------------------------------------------


def test_window_hours_helper():
    from app.services.scheduler import _window_hours

    assert _window_hours(9, 22) == set(range(9, 22))
    # 翌日跨ぎ: 18-2 -> 18..25
    assert _window_hours(18, 2) == set(range(18, 26))


def test_windowed_employee_uses_fitting_pattern():
    """窓(9-16)を持つ通常従業員は、窓に収まるパターンに入れる（配置制限は窓のみ）。"""
    part_time = PatternSpec(
        id=3,
        code="p_0900_1600",
        label="09:00-16:00",
        start=time(9, 0),
        end=time(16, 0),
        category="morning",
    )
    emp = EmployeeSpec(
        id=1,
        name="A",
        weekly_target=7,
        hourly_wage=1000,
        weekly_shifts_pinned=False,
        available_start=9,
        available_end=16,
    )
    result = _make_scheduler(
        patterns=[MORNING, part_time],  # MORNING(9-17,基本)は窓外
        staffing_rules=_hourly((range(9, 16), 1)),  # 9:00-16:00 に1人
        employees=[emp],
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    # 窓に収まる非基本パターンで実際に配置される（1枠も入れない状態にならない）
    assert result.assignments
    assert all(a["shift_type"] == "p_0900_1600" for a in result.assignments)


def test_short_window_employee_scheduled_with_surplus_tolerance():
    """短い窓(9-15)の従業員が、実需要(16時台あり)でも配置される（ADR-0005: α=1）。

    9-15の人は9-14しか埋められない。16時台を埋める9-17の人が9-14も満たすため、
    == だと過剰になり入れなかった。α=1 なら9-14を+1にして入れられる。
    """
    short = _pattern(3, "p_0900_1500", "morning", time(9, 0), time(15, 0))
    full_timer = EmployeeSpec(
        id=1, name="Full", weekly_target=7, hourly_wage=1000, weekly_shifts_pinned=False
    )
    part_timer = EmployeeSpec(
        id=2,
        name="Part",
        weekly_target=7,
        hourly_wage=1000,
        weekly_shifts_pinned=False,
        available_start=9,
        available_end=15,
    )
    # 朝の各時間(9-16)に1人必要（16時台も需要あり）。
    result = _make_scheduler(
        patterns=[MORNING, short],
        staffing_rules=_hourly((range(9, 17), 1)),
        employees=[full_timer, part_timer],
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    # 9-15の人が実際に配置される（1枠も入れない状態にならない）
    assert any(a["employee_id"] == 2 for a in result.assignments)
    # 過剰は各時間 必要人数+α(=2) まで
    coverage: dict[tuple[object, int], int] = defaultdict(int)
    for a in result.assignments:
        for h in _pattern_hours(a["start_time"], a["end_time"]):
            coverage[(a["target_date"], h)] += 1
    assert all(n <= 2 for n in coverage.values())


def test_available_window_blocks_out_of_window_pattern():
    """窓 9-17 の従業員は、窓に収まらない夜勤(17-1)には配置されない。"""
    emp = EmployeeSpec(
        id=1,
        name="A",
        weekly_target=7,
        hourly_wage=1000,
        weekly_shifts_pinned=False,
        available_start=9,
        available_end=17,
    )
    result = _make_scheduler(
        patterns=[MORNING, EVENING],
        staffing_rules=_hourly((MORNING_HOURS, 1)),  # 朝だけ必要
        employees=[emp],
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    # 夜勤(窓外)は一切割り当てられない。朝(窓内)には入る。
    assert all(a["shift_type"] != "evening" for a in result.assignments)
    assert any(a["shift_type"] == "morning" for a in result.assignments)


# ---- 固定カレンダー展開の受け皿(ADR-0007) --------------------------------------


def test_fixed_off_day_as_unavailable_blocks_assignment():
    """固定カレンダーの休み(off)は unavailable として展開され、その日は配置されない。

    ルーターが off→unavailable の AvailabilitySpec を渡す前提の、スケジューラ側検証。
    """
    from app.services.scheduler import AvailabilitySpec

    # 2026-02-05 は木曜。ここを固定休み(unavailable)にする。
    emp = _employee(1, "A")
    sched = ShiftScheduler(
        year=2026,
        month=2,
        employees=[emp],
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 1)),
        availabilities=[
            AvailabilitySpec(employee_id=1, target_date=_date(2026, 2, 5), kind="unavailable")
        ],
        max_solve_seconds=10.0,
    )
    result = sched.solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert all(a["target_date"] != _date(2026, 2, 5) for a in result.assignments)


def test_mandatory_work_forces_assignment():
    """確定出勤(mandatory)は、その日に需要が無くても必ず1シフト配置される(ADR-0009)。"""
    from app.services.scheduler import AvailabilitySpec

    emp = _employee(1, "A")
    sched = ShiftScheduler(
        year=2026,
        month=2,
        employees=[emp],
        patterns=[MORNING],
        staffing_rules={},  # 需要なし。それでも確定出勤の日は入る。
        availabilities=[
            AvailabilitySpec(employee_id=1, target_date=_date(2026, 2, 5), kind="mandatory")
        ],
        max_solve_seconds=10.0,
    )
    result = sched.solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    worked = {a["target_date"] for a in result.assignments if a["employee_id"] == 1}
    assert _date(2026, 2, 5) in worked


def test_mandatory_work_respects_selected_patterns():
    """パターン選択つきの確定出勤は、選んだパターンで必ず配置される(ADR-0009)。

    2/5 に「evening のみ」の確定出勤 → 夜(evening)で入り、朝(morning)には入らない。
    note には対象パターンのコードをカンマ区切りで持つ。
    """
    from app.services.scheduler import AvailabilitySpec

    emp = _employee(1, "A")
    sched = ShiftScheduler(
        year=2026,
        month=2,
        employees=[emp],
        patterns=[MORNING, EVENING],
        staffing_rules={},  # 需要なしでも確定出勤で入る
        availabilities=[
            AvailabilitySpec(
                employee_id=1,
                target_date=_date(2026, 2, 5),
                kind="mandatory",
                note="evening",
            )
        ],
        max_solve_seconds=10.0,
    )
    result = sched.solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    on_day = [a for a in result.assignments if a["target_date"] == _date(2026, 2, 5)]
    assert len(on_day) == 1
    assert on_day[0]["shift_type"] == "evening"  # 選択した evening で配置


# ---- 連勤制限(ADR-0008) ---------------------------------------------------------


def test_no_five_consecutive_work_days():
    """どの従業員も5連勤しない（最大4連勤。生成月内でカウント）。"""
    # 1人だけで朝に毎日1人必要 → 放っておくと毎日勤務(28連勤)になるが、連勤制限で崩れる。
    emp = _employee(1, "A")
    result = _make_scheduler(
        patterns=[MORNING],
        staffing_rules=_hourly((MORNING_HOURS, 1)),
        employees=[emp],
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")

    worked_days = sorted(a["target_date"] for a in result.assignments if a["employee_id"] == 1)
    # 連続日数の最大が4以下であること
    max_run = run = 0
    prev = None
    for d in worked_days:
        run = run + 1 if prev is not None and (d - prev).days == 1 else 1
        max_run = max(max_run, run)
        prev = d
    assert max_run <= 4


# ---- 保険区分ごとの月間実働時間(ADR-0006) ---------------------------------------

# 朝 9:00-17:00 = 実働8h(480分)。保険区分テスト用に worked_minutes を明示する。
MORNING_8H = PatternSpec(
    id=1, code="morning", label="morning",
    start=time(9, 0), end=time(17, 0), category="morning", worked_minutes=480,
)


def _worked_hours(result, emp_id: int) -> float:
    """割当の実働時間(h)を従業員ごとに集計する。全パターンが8h(=480分)前提。"""
    return sum(8 for a in result.assignments if a["employee_id"] == emp_id)


def test_insurance_none_caps_monthly_hours():
    """保険なし(none)の従業員は月79h以下に抑えられる（上限は常にハード）。"""
    emp = EmployeeSpec(
        id=1, name="A", weekly_target=7, hourly_wage=1000,
        weekly_shifts_pinned=False, insurance_type="none",
    )
    # 朝に毎日1人必要（28日）だが、none上限79h=最大9シフトまでしか入れない。
    result = _make_scheduler(
        patterns=[MORNING_8H],
        staffing_rules=_hourly((MORNING_HOURS, 1)),
        employees=[emp],
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert _worked_hours(result, 1) <= 79


def test_insurance_social_enforces_lower_bound():
    """社会保険(social)の従業員は月120h以上働く（下限が需要より優先してハード）。"""
    emps = [
        EmployeeSpec(
            id=i, name=f"E{i}", weekly_target=7, hourly_wage=1000,
            weekly_shifts_pinned=False, insurance_type="social",
        )
        for i in (1, 2)
    ]
    # 朝に毎日1人必要（1人で足りる）でも、2人とも社保下限120h(=15シフト)を満たす。
    result = _make_scheduler(
        patterns=[MORNING_8H],
        staffing_rules=_hourly((MORNING_HOURS, 1)),
        employees=emps,
    ).solve()
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert _worked_hours(result, 1) >= 120
    assert _worked_hours(result, 2) >= 120
