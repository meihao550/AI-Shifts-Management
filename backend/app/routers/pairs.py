from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.deps import AdminUser, CurrentUser
from app.core.database import get_db
from app.models.employee import Employee
from app.models.pair import EmployeePairConstraint
from app.schemas.pair import PairConstraintCreate, PairConstraintRead

router = APIRouter(prefix="/pair-constraints", tags=["pair-constraints"])


def _pair_exists(db: Session, a_id: int, b_id: int) -> bool:
    """(a, b) または (b, a) の組が既に登録されているか。ペアは順序を問わない。"""
    stmt = select(EmployeePairConstraint).where(
        or_(
            (EmployeePairConstraint.employee_a_id == a_id)
            & (EmployeePairConstraint.employee_b_id == b_id),
            (EmployeePairConstraint.employee_a_id == b_id)
            & (EmployeePairConstraint.employee_b_id == a_id),
        )
    )
    return db.execute(stmt).scalar_one_or_none() is not None


# GETメソッドできたら、下の関数を実行。response_model が返す型の定義（app.schemas.pair）。
@router.get("", response_model=list[PairConstraintRead])
def list_pairs(_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return list(db.execute(select(EmployeePairConstraint)).scalars())


@router.post("", response_model=PairConstraintRead, status_code=status.HTTP_201_CREATED)
def create_pair(
    payload: PairConstraintCreate,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    # 両方の従業員が実在するか確認（存在しないIDでの登録を防ぐ）
    for emp_id in (payload.employee_a_id, payload.employee_b_id):
        if db.get(Employee, emp_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"従業員 id={emp_id} が存在しません",
            )

    if _pair_exists(db, payload.employee_a_id, payload.employee_b_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このペアは既に登録されています",
        )

    row = EmployeePairConstraint(
        employee_a_id=payload.employee_a_id,
        employee_b_id=payload.employee_b_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{pair_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pair(
    pair_id: int,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    row = db.get(EmployeePairConstraint, pair_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pair not found")
    db.delete(row)
    db.commit()
