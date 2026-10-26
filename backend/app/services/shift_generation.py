"""シフト自動生成のオーケストレーション（ドメイン処理）。

ルーター(HTTPの関心)から分離し、ここでは一連の流れだけを担う（SRP）:
従業員・パターン・必要人数・希望・NGペア・LLM制約を集め → CP-SAT ソルバーで解き →
結果を保存して ShiftGenerateResult を返す。
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.coverage_outcome import CoverageOutcome
from app.models.employee import Employee, EmployeeAvailability
from app.models.pair import EmployeePairConstraint
from app.models.rule import ShiftPattern
from app.models.shift import Shift, ShiftAssignment, ShiftStatus
from app.schemas.shift import (
    ShiftAssignmentRead,
    ShiftGenerateRequest,
    ShiftGenerateResult,
)
from app.services.holidays import is_holiday
from app.services.llm import derive_constraints_from_text
from app.services.scheduler import (
    AvailabilitySpec,
    CoverageSlot,
    EmployeeSpec,
    LLMConstraints,
    PatternSpec,
    ShiftScheduler,
    worked_minutes_of,
)
from app.services.staffing import default_patterns, load_staffing_map


def _get_or_create_shift(db: Session, year: int, month: int) -> Shift:
    """対象年月の Shift を取得。無ければ draft で作成して返す。"""
    shift = db.execute(
        select(Shift).where(Shift.year == year, Shift.month == month)
    ).scalar_one_or_none()
    if shift is None:
        shift = Shift(year=year, month=month, status=ShiftStatus.draft)
        db.add(shift)
        db.commit()
        db.refresh(shift)
    return shift


def _persist_coverage(db: Session, shift: Shift, coverage: list[CoverageSlot]) -> None:
    """人手不足の履歴(CoverageOutcome)を当該シフト分だけ置き換える（月ごと1スナップショット）。

    再生成のたびに当該 shift_id の行を全削除し、最新の解のカバレッジを入れ直す（assignments と同方針）。
    履歴は「別の月のスナップショットが溜まること」で蓄積され、集計/人手不足予測(ML)の学習データになる。
    weekday・is_holiday は分析/特徴量用に日付から派生させて保存する。
    """
    db.query(CoverageOutcome).filter(CoverageOutcome.shift_id == shift.id).delete()
    for c in coverage:
        db.add(
            CoverageOutcome(
                shift_id=shift.id,
                target_date=c.target_date,
                hour=c.hour,
                day_category=c.day_category,
                weekday=c.target_date.weekday(),
                is_holiday=is_holiday(c.target_date),
                required=c.required,
                filled=c.filled,
                shortage=max(c.required - c.filled, 0),
            )
        )


async def generate(db: Session, payload: ShiftGenerateRequest) -> ShiftGenerateResult:
    """シフトを自動生成して保存し、結果を返す。

    前提を満たさない場合（従業員0人／ピーク必要人数に満たない）は HTTP 400 を送出する。
    use_llm かつ自然言語メモがあれば LLM で制約（全員休み/個別不可/週回数）を抽出してから解く。
    """
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

    # 時間別必要人数（未登録ならデフォルト）。予測側と共有のヘルパーで読む（DRY）。
    staffing_map = load_staffing_map(db)

    availability_rows = list(db.execute(select(EmployeeAvailability)).scalars())

    # 休日/希望日(出勤ソフト)/確定出勤/有給 を AvailabilitySpec 化。
    # 固定カレンダーは「曜日で一括登録」により具体日付の availability として保存されるため、
    # ここでの特別扱いは不要（同じデータをシフト表カレンダーと共有＝同期。ADR-0007/0009）。
    availability_specs = [
        AvailabilitySpec(
            employee_id=a.employee_id,
            target_date=a.target_date,
            kind=a.kind.value,
            shift_type=a.shift_type,
            note=a.note,
        )
        for a in availability_rows
    ]

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
        closed_dates=llm_result.get("closed_dates", []) or [],
    )

    scheduler = ShiftScheduler(
        year=payload.year,
        month=payload.month,
        employees=[
            EmployeeSpec(
                id=e.id,
                name=e.name,
                weekly_target=e.weekly_shifts,
                hourly_wage=e.hourly_wage,
                weekly_shifts_pinned=e.weekly_shifts_pinned,
                is_dual_worker=e.is_dual_worker,
                insurance_type=e.insurance_type,
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
                rest_minutes=p.rest_minutes,
                worked_minutes=worked_minutes_of(p.start_time, p.end_time, p.rest_minutes),
            )
            for p in patterns
        ],
        staffing_rules=staffing_map,
        availabilities=availability_specs,
        llm_constraints=llm_constraints,
        forbidden_pairs=forbidden_pairs,
    )
    result = scheduler.solve()

    shift = _get_or_create_shift(db, payload.year, payload.month)
    # Clear existing assignments
    db.query(ShiftAssignment).filter(ShiftAssignment.shift_id == shift.id).delete()
    for a in result.assignments:
        db.add(ShiftAssignment(shift_id=shift.id, **a))
    # 人手不足の履歴を更新（集計/ML学習データ。assignments と同じコミットで原子的に）。
    _persist_coverage(db, shift, result.coverage)
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
