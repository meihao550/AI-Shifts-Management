"""Employee CRUD + availability endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import AdminUser, CurrentUser
from app.core.database import get_db
from app.models.employee import (
    AvailabilityKind,
    Employee,
    EmployeeAvailability,
    EmployeeFixedSchedule,
    FixedScheduleStatus,
)
from app.schemas.employee import (
    AvailabilityCreate,
    AvailabilityRead,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    FixedScheduleItem,
)

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    active_only: bool = False,
):
    stmt = select(Employee).order_by(Employee.id)
    if active_only:
        stmt = stmt.where(Employee.active.is_(True))
    return list(db.execute(stmt).scalars())


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="employee not found")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(employee, key, value)
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="employee not found")
    db.delete(employee)
    db.commit()
    return None


@router.get("/availabilities", response_model=list[AvailabilityRead])
def list_all_availabilities(
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    year: Annotated[int | None, Query()] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    kind: Annotated[AvailabilityKind | None, Query()] = None,
):
    """全従業員の希望・不可・有給をまとめて取得（年月・種別で絞り込み可）。"""
    stmt = select(EmployeeAvailability)
    if kind is not None:
        stmt = stmt.where(EmployeeAvailability.kind == kind)
    if year is not None and month is not None:
        month_start = date(year, month, 1)
        month_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        stmt = stmt.where(
            EmployeeAvailability.target_date >= month_start,
            EmployeeAvailability.target_date < month_end,
        )
    stmt = stmt.order_by(EmployeeAvailability.target_date)
    return list(db.execute(stmt).scalars())


@router.get("/{employee_id}/availabilities", response_model=list[AvailabilityRead])
def list_availabilities(
    employee_id: int,
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    stmt = (
        select(EmployeeAvailability)
        .where(EmployeeAvailability.employee_id == employee_id)
        .order_by(EmployeeAvailability.target_date)
    )
    return list(db.execute(stmt).scalars())


@router.post(
    "/availabilities",
    response_model=AvailabilityRead,
    status_code=status.HTTP_201_CREATED,
)
def create_availability(
    payload: AvailabilityCreate,
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    row = EmployeeAvailability(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/availabilities/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability(
    availability_id: int,
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    row = db.get(EmployeeAvailability, availability_id)
    if not row:
        raise HTTPException(status_code=404, detail="availability not found")
    db.delete(row)
    db.commit()
    return None


@router.get("/{employee_id}/fixed-schedule", response_model=list[FixedScheduleItem])
def get_fixed_schedule(
    employee_id: int,
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """固定カレンダー（曜日パターン）を取得。行が無い曜日は「指定なし」として省略。"""
    stmt = (
        select(EmployeeFixedSchedule)
        .where(EmployeeFixedSchedule.employee_id == employee_id)
        .order_by(EmployeeFixedSchedule.day_of_week)
    )
    return list(db.execute(stmt).scalars())


@router.put("/{employee_id}/fixed-schedule", response_model=list[FixedScheduleItem])
def put_fixed_schedule(
    employee_id: int,
    items: list[FixedScheduleItem],
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    """固定カレンダーを一括置き換え（送られた曜日だけ残し、他は削除＝指定なし）。"""
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="employee not found")
    # 既存を全削除してから作り直す（差し替え）。重複曜日は後勝ちで畳む。
    db.query(EmployeeFixedSchedule).filter(
        EmployeeFixedSchedule.employee_id == employee_id
    ).delete()
    by_dow: dict[int, str] = {it.day_of_week: it.status for it in items}
    for dow, st in sorted(by_dow.items()):
        db.add(
            EmployeeFixedSchedule(
                employee_id=employee_id,
                day_of_week=dow,
                status=FixedScheduleStatus(st),
            )
        )
    db.commit()
    stmt = (
        select(EmployeeFixedSchedule)
        .where(EmployeeFixedSchedule.employee_id == employee_id)
        .order_by(EmployeeFixedSchedule.day_of_week)
    )
    return list(db.execute(stmt).scalars())
