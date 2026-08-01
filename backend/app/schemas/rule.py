from datetime import time

from pydantic import BaseModel, ConfigDict

from app.models.rule import DayCategory


class ShiftPatternBase(BaseModel):
    code: str
    label: str
    start_time: time
    end_time: time
    is_basic: bool = True
    category: str  # morning | evening | night


class ShiftPatternCreate(ShiftPatternBase):
    pass


class ShiftPatternRead(ShiftPatternBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class StaffingRuleBase(BaseModel):
    day_category: DayCategory
    shift_category: str  # morning | evening | night
    required: int


class StaffingRuleCreate(StaffingRuleBase):
    pass


class StaffingRuleRead(StaffingRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
