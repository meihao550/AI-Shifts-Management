"""User model — represents an authenticated account (admin or employee)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    admin = "admin"
    employee = "employee"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        default=UserRole.employee,
        nullable=False,
    )
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    employee: Mapped["Employee | None"] = relationship("Employee", back_populates="user")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# Avoid circular imports at type-check time
from app.models.employee import Employee  # noqa: E402
