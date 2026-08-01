"""Development-only helpers (seed data, reset)."""

from datetime import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.employee import Employee, EmployeeAvailability
from app.models.rule import DayCategory, ShiftPattern, StaffingRule
from app.models.shift import Shift, ShiftAssignment

router = APIRouter(prefix="/dev", tags=["dev"])
settings = get_settings()


def _require_dev() -> None:
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="dev endpoints disabled")


@router.post("/seed")
def seed(db: Annotated[Session, Depends(get_db)]):
    """Seed default shift patterns, staffing rules, and demo employees."""
    _require_dev()

    if not db.execute(select(ShiftPattern)).first():
        db.add_all(
            [
                ShiftPattern(
                    code="morning",
                    label="朝 09:00-17:00",
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                    is_basic=True,
                    category="morning",
                ),
                ShiftPattern(
                    code="evening",
                    label="夜 17:00-01:00",
                    start_time=time(17, 0),
                    end_time=time(1, 0),
                    is_basic=True,
                    category="evening",
                ),
                ShiftPattern(
                    code="night",
                    label="深夜 01:00-09:00",
                    start_time=time(1, 0),
                    end_time=time(9, 0),
                    is_basic=True,
                    category="night",
                ),
            ]
        )

    if not db.execute(select(StaffingRule)).first():
        db.add_all(
            [
                StaffingRule(day_category=DayCategory.weekday, shift_category="morning", required=2),
                StaffingRule(day_category=DayCategory.weekday, shift_category="evening", required=2),
                StaffingRule(day_category=DayCategory.weekday, shift_category="night", required=1),
                StaffingRule(
                    day_category=DayCategory.weekend_or_holiday,
                    shift_category="morning",
                    required=3,
                ),
                StaffingRule(
                    day_category=DayCategory.weekend_or_holiday,
                    shift_category="evening",
                    required=3,
                ),
                StaffingRule(
                    day_category=DayCategory.weekend_or_holiday,
                    shift_category="night",
                    required=1,
                ),
            ]
        )

    if not db.execute(select(Employee)).first():
        db.add_all(
            [
                Employee(
                    name=f"従業員{i:02d}",
                    email=f"emp{i:02d}@example.com",
                    age=25 + (i % 15),
                    transport_cost=500,
                    hourly_wage=1200,
                    main_shift_type=["morning", "evening", "night"][i % 3],
                    weekly_shifts=3 + (i % 3),
                )
                for i in range(1, 26)
            ]
        )

    db.commit()
    return {"status": "seeded"}


@router.post("/reset")
def reset(db: Annotated[Session, Depends(get_db)]):
    """Drop shifts, availabilities, employees, staffing, patterns — then reseed."""
    _require_dev()
    db.query(ShiftAssignment).delete()
    db.query(Shift).delete()
    db.query(EmployeeAvailability).delete()
    db.query(StaffingRule).delete()
    db.query(ShiftPattern).delete()
    db.query(Employee).delete()
    db.commit()
    return seed(db)
