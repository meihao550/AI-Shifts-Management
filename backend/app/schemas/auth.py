from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

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


class AllowedLoginCreate(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.employee
    employee_id: int | None = None

    @model_validator(mode="after")
    def _employee_requires_link(self) -> "AllowedLoginCreate":
        # 種別が従業員なら、紐付ける従業員の選択を必須にする。
        if self.role == UserRole.employee and self.employee_id is None:
            raise ValueError("種別が従業員の場合は従業員を選択してください")
        return self


class AllowedLoginRead(AllowedLoginCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
