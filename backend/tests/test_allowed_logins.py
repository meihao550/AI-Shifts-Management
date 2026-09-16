"""ログイン許可リスト（AllowedLogin）のスキーマ検証とゲート挙動のテスト。"""

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  全モデルを metadata に登録する
from app.core.database import Base
from app.models.user import AllowedLogin, UserRole
from app.routers.auth import _persist_or_update_user
from app.schemas.auth import AllowedLoginCreate


def _memory_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


# ---- スキーマ ------------------------------------------------------------------


def test_allowed_login_create_defaults_employee():
    obj = AllowedLoginCreate(name="山田", email="yamada@example.com")
    assert obj.role == UserRole.employee


def test_allowed_login_create_rejects_bad_email():
    with pytest.raises(ValidationError):
        AllowedLoginCreate(name="x", email="not-an-email")


# ---- ゲート挙動（許可リスト） ---------------------------------------------------


def test_allowlisted_email_can_login_with_role():
    db = _memory_session()
    db.add(AllowedLogin(name="管理者", email="ok@example.com", role=UserRole.admin))
    db.commit()

    user = _persist_or_update_user(
        db, {"email": "ok@example.com", "name": "OK", "sub": "s1", "picture": None}
    )
    assert user is not None
    assert user.role == UserRole.admin  # 許可リストの権限が反映される


def test_non_allowlisted_email_is_rejected():
    db = _memory_session()
    db.add(AllowedLogin(name="管理者", email="ok@example.com", role=UserRole.admin))
    db.commit()

    user = _persist_or_update_user(
        db, {"email": "stranger@example.com", "name": "X", "sub": "s2", "picture": None}
    )
    assert user is None  # 許可リストに無い → ログイン不可


def test_role_synced_from_allowlist_on_relogin():
    db = _memory_session()
    row = AllowedLogin(name="A", email="a@example.com", role=UserRole.employee)
    db.add(row)
    db.commit()

    u1 = _persist_or_update_user(db, {"email": "a@example.com", "name": "A", "sub": "s"})
    assert u1 is not None and u1.role == UserRole.employee

    row.role = UserRole.admin  # 許可リストで権限を昇格
    db.commit()
    u2 = _persist_or_update_user(db, {"email": "a@example.com", "name": "A", "sub": "s"})
    assert u2 is not None and u2.role == UserRole.admin  # 次回ログインで反映
