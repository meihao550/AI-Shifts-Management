"""Shift patterns + staffing rules routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import AdminUser, CurrentUser
from app.core.database import get_db
from app.models.rule import ShiftPattern, StaffingRule
from app.schemas.rule import (
    ShiftPatternCreate,
    ShiftPatternRead,
    StaffingRuleCreate,
    StaffingRuleRead,
)

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/patterns", response_model=list[ShiftPatternRead])
def list_patterns(_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return list(db.execute(select(ShiftPattern).order_by(ShiftPattern.id)).scalars())


@router.post("/patterns", response_model=ShiftPatternRead, status_code=status.HTTP_201_CREATED)
def create_pattern(
    payload: ShiftPatternCreate,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    pat = ShiftPattern(**payload.model_dump())
    db.add(pat)
    db.commit()
    db.refresh(pat)
    return pat


@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pattern(pattern_id: int, _admin: AdminUser, db: Annotated[Session, Depends(get_db)]):
    row = db.get(ShiftPattern, pattern_id)
    if not row:
        raise HTTPException(status_code=404, detail="pattern not found")
    db.delete(row)
    db.commit()


@router.get("/staffing", response_model=list[StaffingRuleRead])
def list_staffing(_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return list(db.execute(select(StaffingRule).order_by(StaffingRule.id)).scalars())


@router.put("/staffing", response_model=list[StaffingRuleRead])
def replace_staffing(
    payload: list[StaffingRuleCreate],
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    db.execute(StaffingRule.__table__.delete())
    rows = [StaffingRule(**item.model_dump()) for item in payload]
    db.add_all(rows)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows
