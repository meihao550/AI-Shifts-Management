from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.employee import AvailabilityKind, EmployeeRole


class EmployeeBase(BaseModel):
    name: str
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=15, le=99)
    transport_cost: int = Field(default=0, ge=0)
    hourly_wage: int = Field(default=1100, ge=0)
    main_shift_type: str | None = None
    main_shift_pinned: bool = False
    is_dual_worker: bool = False
    weekly_shifts: int = Field(default=3, ge=0, le=7)
    role: EmployeeRole = EmployeeRole.employee
    active: bool = True
    paid_leave_amount: int = Field(default=0, ge=0)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=15, le=99)
    transport_cost: int | None = Field(default=None, ge=0)
    hourly_wage: int | None = Field(default=None, ge=0)
    main_shift_type: str | None = None
    main_shift_pinned: bool | None = None
    is_dual_worker: bool | None = None
    weekly_shifts: int | None = Field(default=None, ge=0, le=7)
    role: EmployeeRole | None = None
    active: bool | None = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AvailabilityCreate(BaseModel):
    employee_id: int
    target_date: date
    shift_type: str | None = None
    kind: AvailabilityKind
    note: str | None = None


class AvailabilityRead(AvailabilityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
