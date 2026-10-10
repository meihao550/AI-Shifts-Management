"""Auth router — Google OAuth login（許可リスト制）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.auth.google import build_authorize_url, exchange_code, fetch_userinfo
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import AllowedLogin, User
from app.schemas.auth import LoginResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _persist_or_update_user(db: Session, info: dict) -> User | None:
    """許可リストに載っている email だけログイン可。許可外なら None を返す。

    role は許可リスト(AllowedLogin)を真実源とし、ログインの度に User へ同期する。
    """
    email = info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="google user has no email")

    domain = email.split("@")[-1]
    if settings.allowed_google_domain and domain != settings.allowed_google_domain:
        return None

    # 許可リスト照合（大文字小文字を無視）
    allowed = db.execute(
        select(AllowedLogin).where(func.lower(AllowedLogin.email) == email.lower())
    ).scalar_one_or_none()
    if allowed is None:
        return None

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            name=info.get("name") or allowed.name or email,
            picture_url=info.get("picture"),
            google_sub=info.get("sub"),
            role=allowed.role,
        )
        db.add(user)
    else:
        user.name = info.get("name") or user.name
        user.picture_url = info.get("picture") or user.picture_url
        user.google_sub = info.get("sub") or user.google_sub
        user.role = allowed.role  # 許可リストの権限を反映
    db.commit()
    db.refresh(user)
    return user


@router.get("/google/login")
def google_login():
    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID is not configured")
    url, _state = build_authorize_url()
    return RedirectResponse(url)


@router.get("/google/callback", response_model=LoginResponse)
async def google_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="missing authorization code")

    try:
        token_resp = await exchange_code(code)
        info = await fetch_userinfo(token_resp["access_token"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"google oauth failed: {exc}") from exc

    frontend = settings.frontend_origin.rstrip("/")

    user = _persist_or_update_user(db, info)
    if user is None:
        # 許可リストに無い / ドメイン不一致 → ログイン画面で優しく通知する。
        return RedirectResponse(f"{frontend}/login?error=not_allowed")

    jwt_token = create_access_token(str(user.id), extra={"role": user.role.value})
    return RedirectResponse(f"{frontend}/auth/callback?token={jwt_token}")


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser) -> MeResponse:
    return MeResponse.model_validate(user)
