"""Employee CRUD + availability endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import AdminUser, CurrentUser
from app.core.database import get_db
from app.models.employee import Employee, EmployeeAvailability
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
