"""ログイン許可リストの管理（管理者専用）。ここに載っている email だけログインできる。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import AdminUser
from app.core.database import get_db
from app.models.user import AllowedLogin, UserRole
from app.schemas.auth import AllowedLoginCreate, AllowedLoginRead

router = APIRouter(prefix="/allowed-logins", tags=["allowed-logins"])


@router.get("", response_model=list[AllowedLoginRead])
def list_allowed(_admin: AdminUser, db: Annotated[Session, Depends(get_db)]):
    return list(db.execute(select(AllowedLogin).order_by(AllowedLogin.id)).scalars())


@router.post("", response_model=AllowedLoginRead, status_code=status.HTTP_201_CREATED)
def create_allowed(
    payload: AllowedLoginCreate,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    email = payload.email.lower()
    existing = db.execute(
        select(AllowedLogin).where(func.lower(AllowedLogin.email) == email)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="この email は既に登録されています")
    row = AllowedLogin(name=payload.name, email=email, role=payload.role)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{allowed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allowed(
    allowed_id: int,
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    row = db.get(AllowedLogin, allowed_id)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    # 最後の管理者を消してログイン不能になる事故を防ぐ。
    if row.role == UserRole.admin:
        admin_count = db.execute(
            select(func.count())
            .select_from(AllowedLogin)
            .where(AllowedLogin.role == UserRole.admin)
        ).scalar_one()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400, detail="最後の管理者は削除できません"
            )
    db.delete(row)
    db.commit()
    return None
