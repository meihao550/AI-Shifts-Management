from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import AdminUser, CurrentUser
from app.core.database import get_db
from app.models.pair import EmployeePairConstraint
from app.schemas.pair import PairConstraintCreate, PairConstraintRead

router = APIRouter(prefix="/pair-constraints", tags=["pair-constraints"])


# GETメソッドできたら、下の関数を実行。第２引数が返す型の定義をしている。`app.schemas.pair`に存在する.
@router.get("", response_model=list[PairConstraintRead])
def list_pairs(_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return list(db.execute(select(EmployeePairConstraint)).scalars())


@router.post("", response_model=list[PairConstraintRead], status_code=status.HTTP_201_CREATED)
def create_pair(
    payload: PairConstraintCreate,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    row = EmployeePairConstraint(
        employee_a_id=payload.employee_a_id,
        employee_b_id=payload.employee_b_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
