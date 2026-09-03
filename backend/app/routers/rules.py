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
    ShiftPatternUpdate,
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
        rest_minutes=payload.rest_minutes,
    )
    db.add(pat)
    db.commit()
    db.refresh(pat)
    return pat


@router.patch("/patterns/{pattern_id}", response_model=ShiftPatternRead)
def update_pattern(
    pattern_id: int,
    payload: ShiftPatternUpdate,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    pat = db.get(ShiftPattern, pattern_id)
    if not pat:
        raise HTTPException(status_code=404, detail="pattern not found")

    updates = payload.model_dump(exclude_unset=True)
    if "label" in updates and updates["label"]:
        pat.label = updates["label"]
    if "rest_minutes" in updates and updates["rest_minutes"] is not None:
        pat.rest_minutes = updates["rest_minutes"]

    # 開始/終了を変えたらコード・区分を再生成する（コードは時刻から自動導出のため）。
    new_start = updates.get("start_time") or pat.start_time
    new_end = updates.get("end_time") or pat.end_time
    if new_start != pat.start_time or new_end != pat.end_time:
        new_code = make_pattern_code(new_start, new_end)
        conflict = db.execute(
            select(ShiftPattern).where(
                ShiftPattern.code == new_code, ShiftPattern.id != pattern_id
            )
        ).scalar_one_or_none()
        if conflict:
            raise HTTPException(
                status_code=409, detail="同じ時間帯のパターンが既に存在します"
            )
        pat.start_time = new_start
        pat.end_time = new_end
        pat.code = new_code
        pat.category = infer_category(new_start, new_end)

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
