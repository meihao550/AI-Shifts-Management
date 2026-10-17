"""JWT + password utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw: str) -> str:
    """平文パスワードをハッシュ化する。"""
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    """平文パスワードとハッシュが一致するか検証する。"""
    return pwd_context.verify(raw, hashed)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """ユーザーID(subject)と追加クレームから JWT アクセストークンを発行する。"""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """JWT を検証してペイロードを返す（無効・期限切れなら例外）。"""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
