"""Shift generation + management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import AdminUser, CurrentUser
from app.core.database import get_db
from app.models.employee import Employee
from app.models.rule import ShiftPattern
from app.models.shift import Shift, ShiftAssignment, ShiftStatus
from app.schemas.shift import (
    ShiftAssignmentCreate,
    ShiftAssignmentRead,
    ShiftGenerateRequest,
    ShiftGenerateResult,
    ShiftRead,
)
from app.services import shift_generation
from app.services.export import export_excel, export_pdf

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.get("", response_model=ShiftRead)
def get_shift(
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
):
    """指定した年月のシフト表を割当込みで返す（無ければ404）。"""
    shift = db.execute(
        select(Shift)
        .options(selectinload(Shift.assignments))
        .where(Shift.year == year, Shift.month == month)
    ).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="shift not found")
    return shift


@router.post("/generate", response_model=ShiftGenerateResult)
async def generate_shift(
    payload: ShiftGenerateRequest,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    """シフトを自動生成する（管理者のみ）。処理本体は services.shift_generation.generate。"""
    return await shift_generation.generate(db, payload)


@router.put("/{shift_id}/assignments", response_model=list[ShiftAssignmentRead])
def replace_assignments(
    shift_id: int,
    assignments: list[ShiftAssignmentCreate],
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    """シフトの割当を丸ごと差し替える（手動編集の保存。管理者のみ）。"""
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="shift not found")
    # 休憩は shift_type(=パターンcode)からパターンの rest_minutes を引いて焼き込む
    # （パターンが唯一の真実源。クライアント送信値は使わない。ADR 0001 参照）。
    rest_by_code = {
        row.code: row.rest_minutes
        for row in db.execute(
            select(ShiftPattern.code, ShiftPattern.rest_minutes)
        ).all()
    }
    db.query(ShiftAssignment).filter(ShiftAssignment.shift_id == shift_id).delete()
    rows = []
    for a in assignments:
        data = a.model_dump()
        data["rest_minutes"] = rest_by_code.get(a.shift_type, 0)
        rows.append(ShiftAssignment(shift_id=shift_id, **data))
    db.add_all(rows)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows


@router.post("/{shift_id}/finalize", response_model=ShiftRead)
def finalize(
    shift_id: int,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    """シフトのステータスを finalized（確定）にする（管理者のみ）。"""
    shift = db.execute(
        select(Shift).options(selectinload(Shift.assignments)).where(Shift.id == shift_id)
    ).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="shift not found")
    shift.status = ShiftStatus.finalized
    db.commit()
    db.refresh(shift)
    return shift


@router.get("/{shift_id}/export/pdf")
def export_shift_pdf(
    shift_id: int,
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """シフト表を PDF でダウンロードする。"""
    shift = _load_shift_with_deps(db, shift_id)
    employees = list(db.execute(select(Employee).order_by(Employee.id)).scalars())
    pdf = export_pdf(shift.year, shift.month, list(shift.assignments), employees)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="shift-{shift.year}-{shift.month:02d}.pdf"'
        },
    )


@router.get("/{shift_id}/export/excel")
def export_shift_excel(
    shift_id: int,
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """シフト表を Excel でダウンロードする。"""
    shift = _load_shift_with_deps(db, shift_id)
    employees = list(db.execute(select(Employee).order_by(Employee.id)).scalars())
    xlsx = export_excel(shift.year, shift.month, list(shift.assignments), employees)
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="shift-{shift.year}-{shift.month:02d}.xlsx"'
        },
    )


def _load_shift_with_deps(db: Session, shift_id: int) -> Shift:
    shift = db.execute(
        select(Shift).options(selectinload(Shift.assignments)).where(Shift.id == shift_id)
    ).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="shift not found")
    return shift
