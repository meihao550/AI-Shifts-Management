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


def _make_employee(id_, name, hourly_wage=1200, transport=500):
    return SimpleNamespace(
        id=id_, name=name, hourly_wage=hourly_wage, transport_cost=transport
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


def test_calculate_payroll_insurance_thresholds():
    emp = _make_employee(1, "田中")
    # 120時間 = social
    assignments = [_make_assignment(1, f"2025-06-{i:02d}", "09:00", "17:00") for i in range(1, 16)]
    report = calculate_payroll(2025, 6, assignments, {1: emp})
    assert report.rows[0].total_hours == 120.0
    assert report.rows[0].insurance_status == "social"
