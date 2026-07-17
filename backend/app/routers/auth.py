"""Auth router — Google OAuth login + dev token issuance."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.auth.google import build_authorize_url, exchange_code, fetch_userinfo
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.schemas.auth import LoginResponse, MeResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _persist_or_update_user(db: Session, info: dict) -> User:
    email = info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="google user has no email")

    domain = email.split("@")[-1]
    if settings.allowed_google_domain and domain != settings.allowed_google_domain:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"only {settings.allowed_google_domain} accounts are allowed",
        )

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    is_first_user = db.execute(select(User).limit(1)).scalar_one_or_none() is None

    if user is None:
        user = User(
            email=email,
            name=info.get("name") or email,
            picture_url=info.get("picture"),
            google_sub=info.get("sub"),
            role=UserRole.admin if is_first_user else UserRole.employee,
        )
        db.add(user)
    else:
        user.name = info.get("name") or user.name
        user.picture_url = info.get("picture") or user.picture_url
        user.google_sub = info.get("sub") or user.google_sub
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

    user = _persist_or_update_user(db, info)
    jwt_token = create_access_token(str(user.id), extra={"role": user.role.value})

    frontend = settings.frontend_origin.rstrip("/")
    return RedirectResponse(f"{frontend}/auth/callback?token={jwt_token}")


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser) -> MeResponse:
    return MeResponse.model_validate(user)


@router.post("/dev-login", response_model=LoginResponse)
def dev_login(
    email: str,
    name: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Development-only helper. Disabled outside `development` env."""
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="not available")

    user = _persist_or_update_user(
        db,
        {"email": email, "name": name, "sub": f"dev-{email}", "picture": None},
    )
    # dev-login で作られた/呼ばれたユーザは常に admin に昇格
    if user.role != UserRole.admin:
        user.role = UserRole.admin
        db.commit()
        db.refresh(user)
    jwt_token = create_access_token(str(user.id), extra={"role": user.role.value})
    return LoginResponse(
        token=Token(access_token=jwt_token),
        user=MeResponse.model_validate(user),
    )
