from datetime import date, time
from types import SimpleNamespace

from app.services.payroll import calculate_payroll


def _make_assignment(emp_id, d, start, end, crosses=False):
    return SimpleNamespace(
        employee_id=emp_id,
        target_date=date.fromisoformat(d),
        shift_type="test",
        start_time=time.fromisoformat(start),
        end_time=time.fromisoformat(end),
        crosses_midnight=crosses,
    )


def _make_employee(id_, name, hourly_wage=1200, transport=500, paid_leave_amount=0):
    return SimpleNamespace(
        id=id_,
        name=name,
        hourly_wage=hourly_wage,
        transport_cost=transport,
        paid_leave_amount=paid_leave_amount,
    )


def test_calculate_payroll_basic_shift():
    emp = _make_employee(1, "田中")
    a = _make_assignment(1, "2025-06-02", "09:00", "17:00")
    report = calculate_payroll(2025, 6, [a], {1: emp})
    row = report.rows[0]
    assert row.total_hours == 8.0
    assert row.overnight_hours == 0.0
    assert row.base_wage == 8 * 1200
    assert row.overnight_premium == 0
    assert row.insurance_status == "none"


def test_calculate_payroll_night_shift_with_premium():
    emp = _make_employee(1, "田中")
    # 深夜 01:00–09:00: 01:00-05:00 の 4h が深夜帯
    a = _make_assignment(1, "2025-06-02", "01:00", "09:00")
    report = calculate_payroll(2025, 6, [a], {1: emp})
    row = report.rows[0]
    assert row.total_hours == 8.0
    assert row.overnight_hours == 4.0
    assert row.overnight_premium == int(4 * 1200 * 0.25)


def test_employee_without_assignment_appears_with_zero():
    # 割当のない従業員も 0 円の行として一覧に含まれる（集計漏れの回帰防止）
    emp1 = _make_employee(1, "田中")
    emp2 = _make_employee(2, "佐藤")
    a = _make_assignment(1, "2025-06-02", "09:00", "17:00")  # emp1 のみ勤務
    report = calculate_payroll(2025, 6, [a], {1: emp1, 2: emp2})

    assert len(report.rows) == 2
    by_id = {r.employee_id: r for r in report.rows}
    assert by_id[2].total_hours == 0.0
    assert by_id[2].grand_total == 0
    assert by_id[2].insurance_status == "none"


def test_paid_leave_added_to_cost_not_hours():
    # 有給は勤務時間に加算せず、人件費(有給日数 × 日額)にのみ加算する
    emp = _make_employee(1, "田中", paid_leave_amount=9000)
    a = _make_assignment(1, "2025-06-02", "09:00", "17:00")  # 通常勤務 8h
    paid_leave = [(1, date.fromisoformat("2025-06-10")), (1, date.fromisoformat("2025-06-11"))]
    report = calculate_payroll(2025, 6, [a], {1: emp}, paid_leave)

    row = report.rows[0]
    assert row.total_hours == 8.0  # 有給日は勤務時間に含めない
    assert row.paid_leave_days == 2
    assert row.paid_leave_total == 2 * 9000
    assert row.grand_total == row.base_wage + row.transport_cost_total + 2 * 9000
    # 日別人件費にも有給が計上される
    by_date = {d.target_date.isoformat(): d for d in report.per_day}
    assert by_date["2025-06-10"].total_cost == 9000


def test_calculate_payroll_insurance_thresholds():
    emp = _make_employee(1, "田中")
    # 120時間 = social
    assignments = [_make_assignment(1, f"2025-06-{i:02d}", "09:00", "17:00") for i in range(1, 16)]
    report = calculate_payroll(2025, 6, assignments, {1: emp})
    assert report.rows[0].total_hours == 120.0
    assert report.rows[0].insurance_status == "social"
