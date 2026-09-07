"""Development-only helpers (seed data, reset)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.employee import Employee, EmployeeAvailability
from app.models.rule import HourlyStaffingRule, ShiftPattern
from app.models.shift import Shift, ShiftAssignment
from app.services.staffing import default_hourly_rules, default_patterns

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
        db.add_all([ShiftPattern(**p) for p in default_patterns()])

    if not db.execute(select(HourlyStaffingRule)).first():
        db.add_all([HourlyStaffingRule(**r) for r in default_hourly_rules()])

    if not db.execute(select(Employee)).first():
        db.add_all(
            [
                Employee(
                    name=f"従業員{i:02d}",
                    email=f"emp{i:02d}@example.com",
                    age=25 + (i % 15),
                    transport_cost=500,
                    hourly_wage=1200,
                    weekly_shifts=3 + (i % 3),
                    # 5人に1人を Wワーク（掛け持ち）従業員として登録（デモ用）
                    is_dual_worker=(i % 5 == 0),
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
    db.query(HourlyStaffingRule).delete()
    db.query(ShiftPattern).delete()
    db.query(Employee).delete()
    db.commit()
    return seed(db)
