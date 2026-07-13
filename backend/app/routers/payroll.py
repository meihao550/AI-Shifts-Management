"""Payroll (labor cost) endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import CurrentUser
from app.core.database import get_db
from app.models.employee import Employee
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

    employees = list(db.execute(select(Employee)).scalars())
    employees_by_id = {e.id: e for e in employees}
    return calculate_payroll(year, month, shift.assignments, employees_by_id)
