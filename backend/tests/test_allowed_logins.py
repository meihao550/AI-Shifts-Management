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
    # 既定ロールは従業員。従業員ロールは紐付ける従業員(employee_id)が必須。
    obj = AllowedLoginCreate(name="山田", email="yamada@example.com", employee_id=1)
    assert obj.role == UserRole.employee
    assert obj.employee_id == 1


def test_allowed_login_employee_requires_employee_id():
    # 種別が従業員で employee_id 未指定は不可。
    with pytest.raises(ValidationError):
        AllowedLoginCreate(name="山田", email="yamada@example.com")


def test_allowed_login_admin_allows_no_employee():
    # 管理者は従業員の紐付けなしで作成できる。
    obj = AllowedLoginCreate(name="管理者", email="admin@example.com", role=UserRole.admin)
    assert obj.employee_id is None


def test_allowed_login_create_rejects_bad_email():
    with pytest.raises(ValidationError):
        AllowedLoginCreate(name="x", email="not-an-email", employee_id=1)


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
