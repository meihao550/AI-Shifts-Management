"""Shift patterns + staffing rules routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import AdminUser, CurrentUser
from app.core.database import get_db
from app.models.rule import HourlyStaffingRule, ShiftPattern
from app.schemas.rule import (
    HourlyStaffingRuleCreate,
    HourlyStaffingRuleRead,
    ShiftPatternCreate,
    ShiftPatternRead,
)
from app.services.staffing import infer_category, make_pattern_code, make_pattern_label

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
    # 時刻からコード・表示名・区分を自動生成する。ユーザーが追加するパターンは
    # Wワーク扱い(is_basic=False)＝通常従業員には割り当てない。
    code = make_pattern_code(payload.start_time, payload.end_time)
    existing = db.execute(
        select(ShiftPattern).where(ShiftPattern.code == code)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="同じ時間帯のパターンが既に存在します")
    pat = ShiftPattern(
        code=code,
        label=payload.label or make_pattern_label(payload.start_time, payload.end_time),
        start_time=payload.start_time,
        end_time=payload.end_time,
        is_basic=False,
        category=infer_category(payload.start_time, payload.end_time),
    )
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


@router.get("/hourly-staffing", response_model=list[HourlyStaffingRuleRead])
def list_hourly_staffing(_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return list(
        db.execute(
            select(HourlyStaffingRule).order_by(
                HourlyStaffingRule.day_category, HourlyStaffingRule.hour
            )
        ).scalars()
    )


@router.put("/hourly-staffing", response_model=list[HourlyStaffingRuleRead])
def replace_hourly_staffing(
    payload: list[HourlyStaffingRuleCreate],
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    db.execute(HourlyStaffingRule.__table__.delete())
    rows = [HourlyStaffingRule(**item.model_dump()) for item in payload]
    db.add_all(rows)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows
