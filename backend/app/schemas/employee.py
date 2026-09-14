from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.employee import AvailabilityKind, EmployeeRole

# 保険区分(マスタ属性)。payroll の InsuranceStatus と同じ語彙。
InsuranceType = Literal["social", "employment", "none"]


class EmployeeBase(BaseModel):
    name: str
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=15, le=99)
    transport_cost: int = Field(default=0, ge=0)
    hourly_wage: int = Field(default=1100, ge=0)
    is_dual_worker: bool = False
    weekly_shifts: int = Field(default=3, ge=0, le=7)
    # 週回数を完全週でちょうど weekly_shifts 回のハード制約にするか(ADR-0003)。新規は既定 True。
    weekly_shifts_pinned: bool = True
    role: EmployeeRole = EmployeeRole.employee
    active: bool = True
    paid_leave_amount: int = Field(default=0, ge=0)
    # 保険区分(マスタ属性)。月間実働時間のハード制約に使う(ADR-0006)。
    insurance_type: InsuranceType = "none"
    # 普段入れる時間帯（1時間単位, 0〜24）。両方 None なら制限なし。
    available_start_hour: int | None = Field(default=None, ge=0, le=24)
    available_end_hour: int | None = Field(default=None, ge=0, le=24)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=15, le=99)
    transport_cost: int | None = Field(default=None, ge=0)
    hourly_wage: int | None = Field(default=None, ge=0)
    paid_leave_amount: int | None = Field(default=None, ge=0)
    is_dual_worker: bool | None = None
    weekly_shifts: int | None = Field(default=None, ge=0, le=7)
    weekly_shifts_pinned: bool | None = None
    insurance_type: InsuranceType | None = None
    role: EmployeeRole | None = None
    active: bool | None = None
    available_start_hour: int | None = Field(default=None, ge=0, le=24)
    available_end_hour: int | None = Field(default=None, ge=0, le=24)


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
