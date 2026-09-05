"""Shift generation + management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import AdminUser, CurrentUser
from app.core.database import get_db
from app.models.employee import Employee, EmployeeAvailability
from app.models.pair import EmployeePairConstraint
from app.models.rule import HourlyStaffingRule, ShiftPattern
from app.models.shift import Shift, ShiftAssignment, ShiftStatus
from app.schemas.shift import (
    ShiftAssignmentCreate,
    ShiftAssignmentRead,
    ShiftGenerateRequest,
    ShiftGenerateResult,
    ShiftRead,
)
from app.services.export import export_excel, export_pdf
from app.services.llm import derive_constraints_from_text
from app.services.scheduler import (
    AvailabilitySpec,
    EmployeeSpec,
    LLMConstraints,
    PatternSpec,
    ShiftScheduler,
)
from app.services.staffing import default_hourly_rules, default_patterns

router = APIRouter(prefix="/shifts", tags=["shifts"])


def _get_or_create_shift(db: Session, year: int, month: int) -> Shift:
    shift = db.execute(
        select(Shift).where(Shift.year == year, Shift.month == month)
    ).scalar_one_or_none()
    if shift is None:
        shift = Shift(year=year, month=month, status=ShiftStatus.draft)
        db.add(shift)
        db.commit()
        db.refresh(shift)
    return shift


@router.get("", response_model=ShiftRead)
def get_shift(
    _user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
):
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
    employees = list(db.execute(select(Employee).where(Employee.active.is_(True))).scalars())
    if not employees:
        raise HTTPException(
            status_code=400,
            detail="有効な従業員がいません。従業員管理画面から追加してください。",
        )

    patterns = list(db.execute(select(ShiftPattern)).scalars())
    if not patterns:
        # Auto-seed defaults (基本 + Wワーク) so first-time users can generate immediately.
        db.add_all([ShiftPattern(**p) for p in default_patterns()])
        db.commit()
        patterns = list(db.execute(select(ShiftPattern)).scalars())

    staffing_rows = list(db.execute(select(HourlyStaffingRule)).scalars())
    staffing_map: dict[tuple[str, int], int] = {
        (r.day_category.value, r.hour): r.required for r in staffing_rows
    }
    if not staffing_map:
        # 時間別必要人数のデフォルト（時間カバレッジ方式）
        staffing_map = {
            (r["day_category"].value, r["hour"]): r["required"]
            for r in default_hourly_rules()
        }

    availability_rows = list(db.execute(select(EmployeeAvailability)).scalars())

    # 禁止ペア（ハード制約 H-6）を読み込み、(a_id, b_id) のタプル列にする
    pair_rows = list(db.execute(select(EmployeePairConstraint)).scalars())
    forbidden_pairs = [(p.employee_a_id, p.employee_b_id) for p in pair_rows]

    # ピーク時（1 時間で最も多くの人数が必要な時間帯）を下回る人数しかいなければ、
    # どうやっても各時間を満たせないので早めに知らせる。
    peak_demand = max(staffing_map.values(), default=0)
    if len(employees) < peak_demand:
        raise HTTPException(
            status_code=400,
            detail=(
                f"必要人員 (ピーク時 {peak_demand} 名) に対して有効な従業員が "
                f"{len(employees)} 名しかいません。従業員を追加するか、"
                "ルール設定で必要人員を減らしてください。"
            ),
        )

    llm_result: dict = {}
    if payload.use_llm and payload.natural_language_note:
        employees_hint = [{"id": e.id, "name": e.name} for e in employees]
        llm_result = await derive_constraints_from_text(
            payload.natural_language_note,
            employees_hint,
            payload.year,
            payload.month,
        )

    llm_constraints = LLMConstraints(
        hard_unavailable=llm_result.get("hard_unavailable", []) or [],
        max_shifts_per_week_override=llm_result.get("max_shifts_per_week_override", {}) or {},
        date_notes=llm_result.get("date_notes", {}) or {},
    )

    scheduler = ShiftScheduler(
        year=payload.year,
        month=payload.month,
        employees=[
            EmployeeSpec(
                id=e.id,
                name=e.name,
                weekly_target=e.weekly_shifts,
                main_shift_type=e.main_shift_type,
                hourly_wage=e.hourly_wage,
                main_shift_pinned=e.main_shift_pinned,
                is_dual_worker=e.is_dual_worker,
                available_start=e.available_start_hour,
                available_end=e.available_end_hour,
            )
            for e in employees
        ],
        patterns=[
            PatternSpec(
                id=p.id,
                code=p.code,
                label=p.label,
                start=p.start_time,
                end=p.end_time,
                category=p.category,
                is_basic=p.is_basic,
                rest_minutes=p.rest_minutes,
            )
            for p in patterns
        ],
        staffing_rules=staffing_map,
        availabilities=[
            AvailabilitySpec(
                employee_id=a.employee_id,
                target_date=a.target_date,
                kind=a.kind.value,
                shift_type=a.shift_type,
                note=a.note,
            )
            for a in availability_rows
        ],
        llm_constraints=llm_constraints,
        forbidden_pairs=forbidden_pairs,
    )
    result = scheduler.solve()

    shift = _get_or_create_shift(db, payload.year, payload.month)
    # Clear existing assignments
    db.query(ShiftAssignment).filter(ShiftAssignment.shift_id == shift.id).delete()
    for a in result.assignments:
        db.add(ShiftAssignment(shift_id=shift.id, **a))
    shift.note = payload.natural_language_note
    db.commit()

    saved = db.execute(
        select(Shift).options(selectinload(Shift.assignments)).where(Shift.id == shift.id)
    ).scalar_one()

    return ShiftGenerateResult(
        shift_id=saved.id,
        year=saved.year,
        month=saved.month,
        status=saved.status,
        assignments=[ShiftAssignmentRead.model_validate(a) for a in saved.assignments],
        solver_status=result.solver_status,
        solver_seconds=result.solver_seconds,
        llm_derived_constraints=llm_result or None,
        warnings=result.warnings + (llm_result.get("warnings", []) if llm_result else []),
    )


@router.put("/{shift_id}/assignments", response_model=list[ShiftAssignmentRead])
def replace_assignments(
    shift_id: int,
    assignments: list[ShiftAssignmentCreate],
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
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
