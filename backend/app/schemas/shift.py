from datetime import date, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.shift import ShiftStatus


class ShiftAssignmentBase(BaseModel):
    employee_id: int
    target_date: date
    shift_type: str
    start_time: time
    end_time: time
    crosses_midnight: bool = False


class ShiftAssignmentCreate(ShiftAssignmentBase):
    pass


class ShiftAssignmentRead(ShiftAssignmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    shift_id: int


class ShiftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    year: int
    month: int
    status: ShiftStatus
    note: str | None = None
    assignments: list[ShiftAssignmentRead] = []


class ShiftGenerateRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    natural_language_note: str | None = Field(
        default=None,
        description="今月特有の事情（イベント・希望・調整事項）を自然言語で",
    )
    # If true, LLM parses the note; otherwise treat as free text only
    use_llm: bool = True


class ShiftGenerateResult(BaseModel):
    shift_id: int
    year: int
    month: int
    status: ShiftStatus
    assignments: list[ShiftAssignmentRead]
    solver_status: str
    solver_seconds: float
    llm_derived_constraints: dict[str, Any] | None = None
    warnings: list[str] = []
