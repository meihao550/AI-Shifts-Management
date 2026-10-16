"""Employee CRUD + availability endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import AdminUser, CurrentUser
from app.core.database import get_db
from app.core.dates import month_range
from app.models.employee import AvailabilityKind, Employee, EmployeeAvailability
from app.schemas.employee import (
    AvailabilityCreate,
    AvailabilityRead,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
)

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    active_only: bool = False,
):
    """従業員一覧を返す（active_only=True なら在籍中のみ）。"""
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
    """従業員を新規作成する（管理者のみ）。"""
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
    """従業員を部分更新する（送られた項目だけ上書き。管理者のみ）。"""
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
    """従業員を削除する（希望・シフト割当は CASCADE で連鎖削除。管理者のみ）。"""
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
        month_start, month_end = month_range(year, month)
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
    """指定した従業員の希望・不可・有給（availability）一覧を返す。"""
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
    """希望・不可・有給（availability）を1件登録する。"""
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
    """希望・不可・有給（availability）を1件削除する。"""
    row = db.get(EmployeeAvailability, availability_id)
    if not row:
        raise HTTPException(status_code=404, detail="availability not found")
    db.delete(row)
    db.commit()
    return None
