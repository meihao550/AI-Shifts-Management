from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    picture_url: str | None = None
    role: UserRole
    employee_id: int | None = None


class LoginResponse(BaseModel):
    token: Token
    user: MeResponse
