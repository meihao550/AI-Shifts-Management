"""Payroll (labor cost) endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import CurrentUser
from app.core.database import get_db
from app.models.employee import AvailabilityKind, Employee, EmployeeAvailability
from app.models.rule import ShiftPattern
from app.models.shift import Shift
from app.schemas.payroll import PayrollReport
from app.services.payroll import calculate_payroll

router = APIRouter(prefix="/payroll", tags=["payroll"])


@router.get("", response_model=PayrollReport)
def get_payroll(
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
):
    shift = db.execute(
        select(Shift)
        .options(selectinload(Shift.assignments))
        .where(Shift.year == year, Shift.month == month)
    ).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="shift for this month not found")

    # 在籍中の従業員を集計対象にする（0 出勤でも一覧に表示する）
    employees = list(db.execute(select(Employee).where(Employee.active.is_(True))).scalars())
    employees_by_id = {e.id: e for e in employees}

    # 当月の有給日を集計対象にする（(従業員ID, 日付) の一覧）
    month_start = date(year, month, 1)
    month_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    paid_leave_rows = db.execute(
        select(EmployeeAvailability.employee_id, EmployeeAvailability.target_date).where(
            EmployeeAvailability.kind == AvailabilityKind.paid_leave,
            EmployeeAvailability.target_date >= month_start,
            EmployeeAvailability.target_date < month_end,
        )
    ).all()
    paid_leave_records = [(r.employee_id, r.target_date) for r in paid_leave_rows]

    # 休憩は「現在のパターン」を計算時に都度参照する（shift_type=code → rest_minutes）。
    # これにより、パターンの休憩を変えれば再計算するだけで人件費に反映される（ADR 0001）。
    rest_by_code = {
        row.code: row.rest_minutes
        for row in db.execute(select(ShiftPattern.code, ShiftPattern.rest_minutes)).all()
    }

    return calculate_payroll(
        year, month, shift.assignments, employees_by_id, paid_leave_records, rest_by_code
    )
