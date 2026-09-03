"""Payroll (labor cost) calculation.

Assumptions (per Project.pdf / 要件9.1):
  - 割増賃金は「深夜帯 22:00–翌 5:00」を 25% 増しで計算し、人件費に含める
  - 交通費は 1 出勤あたり `employee.transport_cost` 円で計上
  - 有給は「有給日数 × 有給1日あたりの金額(employee.paid_leave_amount)」を人件費に加算する。
    勤務時間には加算しない（保険判定にも影響しない）＝要件F-3
  - 保険判定は月間労働時間で行う:
        social:      120h 以上
        employment:   80–119h
        none:         79h 以下

TODO (先方確認事項):
  - 交通費の月上限（現状: 出勤日数 × 単価）
  - 社会保険料の会社負担分を人件費に含めるか（→ 要件21章 段階的算入）
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from app.models.employee import Employee
from app.models.shift import ShiftAssignment
from app.schemas.payroll import InsuranceStatus, PayrollDay, PayrollReport, PayrollRow

OVERNIGHT_START = time(22, 0)
OVERNIGHT_END = time(5, 0)
OVERNIGHT_PREMIUM_RATE = 0.25


def _assignment_intervals(a: ShiftAssignment) -> tuple[datetime, datetime]:
    start = datetime.combine(a.target_date, a.start_time)
    end_date = a.target_date + timedelta(days=1) if a.crosses_midnight else a.target_date
    end = datetime.combine(end_date, a.end_time)
    if end <= start:
        end = end + timedelta(days=1)
    return start, end


def _overnight_hours(start: datetime, end: datetime) -> float:
    """Hours worked within the 22:00–翌 5:00 overnight band.

    Within any calendar day the band splits into two sub-windows:
    the early-morning tail ``[00:00, 05:00)`` (belonging to the previous
    night) and the late-night head ``[22:00, 24:00)``. Both must be checked;
    considering only ``[22:00, tomorrow 05:00)`` would miss early-morning
    hours such as a 01:00–09:00 shift.
    """
    total = 0.0
    cursor = start
    while cursor < end:
        day = cursor.date()
        day_end = datetime.combine(day + timedelta(days=1), time.min)
        chunk_end = min(end, day_end)
        windows = (
            (datetime.combine(day, time.min), datetime.combine(day, OVERNIGHT_END)),
            (datetime.combine(day, OVERNIGHT_START), day_end),
        )
        for w_start, w_end in windows:
            seg_start = max(cursor, w_start)
            seg_end = min(chunk_end, w_end)
            if seg_start < seg_end:
                total += (seg_end - seg_start).total_seconds() / 3600.0
        cursor = day_end
    return total


def _classify_insurance(monthly_hours: float) -> InsuranceStatus:
    if monthly_hours >= 120:
        return "social"
    if monthly_hours >= 80:
        return "employment"
    return "none"


def calculate_payroll(
    year: int,
    month: int,
    assignments: Iterable[ShiftAssignment],
    employees_by_id: dict[int, Employee],
    paid_leave_records: Iterable[tuple[int, date]] | None = None,
) -> PayrollReport:
    by_emp: dict[int, list[ShiftAssignment]] = defaultdict(list)
    for a in assignments:
        by_emp[a.employee_id].append(a)

    # 有給日を従業員ごと・日付ごとに集計する（勤務時間には加算せず人件費にのみ計上）。
    paid_leave_dates_by_emp: dict[int, list[date]] = defaultdict(list)
    for emp_id, d in paid_leave_records or []:
        paid_leave_dates_by_emp[emp_id].append(d)

    rows: list[PayrollRow] = []
    warnings: list[str] = []
    per_day_totals: dict[date, dict[str, int]] = defaultdict(lambda: {"total_cost": 0, "headcount": 0})

    # 割当のある従業員だけでなく、渡された全従業員を集計する。
    # 0 出勤の従業員も 0 円の行として表示する（集計から漏れないようにする）。
    for emp_id, emp in sorted(employees_by_id.items()):
        emp_assignments = by_emp.get(emp_id, [])

        total_hours = 0.0  # 総スパン（拘束時間）
        worked_hours = 0.0  # 実働（総スパン − 休憩）。賃金・保険の基礎（ADR 0001）
        overnight_hours = 0.0

        for a in emp_assignments:
            start, end = _assignment_intervals(a)
            span = (end - start).total_seconds() / 3600.0
            rest = (a.rest_minutes or 0) / 60.0
            if rest > span:
                # 設定ミス（休憩が拘束時間を超える）。実働は 0 にクランプし警告する。
                warnings.append(
                    f"{emp.name} {a.target_date.isoformat()}: 休憩({a.rest_minutes}分)が"
                    f"勤務時間({span:.1f}h)を超えています。実働を0として計算しました。"
                )
            worked = max(0.0, span - rest)
            total_hours += span
            worked_hours += worked
            # 深夜割増は総スパンの深夜帯に対して計算する（休憩は昼間仮定・ADR 0001）
            overnight_hours += _overnight_hours(start, end)

            # daily cost (base only, without insurance) - approximation for per-day view
            day_cost = int(worked * emp.hourly_wage)
            night_cost = int(_overnight_hours(start, end) * emp.hourly_wage * OVERNIGHT_PREMIUM_RATE)
            per_day_totals[a.target_date]["total_cost"] += day_cost + night_cost + emp.transport_cost
            per_day_totals[a.target_date]["headcount"] += 1

        base_wage = int(worked_hours * emp.hourly_wage)
        overnight_premium = int(overnight_hours * emp.hourly_wage * OVERNIGHT_PREMIUM_RATE)
        transport_cost_total = emp.transport_cost * len(emp_assignments)
        insurance = _classify_insurance(worked_hours)

        # 有給: 日数 × 有給1日あたりの金額（勤務時間・保険判定には影響しない）
        paid_leave_dates = paid_leave_dates_by_emp.get(emp_id, [])
        paid_leave_days = len(paid_leave_dates)
        paid_leave_total = paid_leave_days * emp.paid_leave_amount
        for d in paid_leave_dates:
            per_day_totals[d]["total_cost"] += emp.paid_leave_amount

        grand = base_wage + overnight_premium + transport_cost_total + paid_leave_total
        rows.append(
            PayrollRow(
                employee_id=emp.id,
                employee_name=emp.name,
                total_hours=round(total_hours, 2),
                worked_hours=round(worked_hours, 2),
                overnight_hours=round(overnight_hours, 2),
                base_wage=base_wage,
                overnight_premium=overnight_premium,
                transport_cost_total=transport_cost_total,
                paid_leave_days=paid_leave_days,
                paid_leave_total=paid_leave_total,
                insurance_status=insurance,
                grand_total=grand,
            )
        )

    per_day = [
        PayrollDay(
            target_date=d,
            total_cost=payload["total_cost"],
            headcount=payload["headcount"],
        )
        for d, payload in sorted(per_day_totals.items())
    ]

    return PayrollReport(
        year=year,
        month=month,
        rows=sorted(rows, key=lambda r: r.employee_id),
        per_day=per_day,
        monthly_total=sum(r.grand_total for r in rows),
        warnings=warnings,
    )
