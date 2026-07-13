"""Shift + ShiftAssignment models."""

from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ShiftStatus(str, Enum):
    draft = "draft"
    published = "published"
    finalized = "finalized"


class Shift(Base):
    """Represents a single month's schedule (a container for daily assignments)."""

    __tablename__ = "shifts"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_shift_month"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ShiftStatus] = mapped_column(
        SAEnum(ShiftStatus, name="shift_status"),
        default=ShiftStatus.draft,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    assignments: Mapped[list["ShiftAssignment"]] = relationship(
        "ShiftAssignment",
        back_populates="shift",
        cascade="all, delete-orphan",
    )


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"
    __table_args__ = (
        UniqueConstraint(
            "shift_id", "target_date", "employee_id", "start_time", name="uq_assignment"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shift_id: Mapped[int] = mapped_column(
        ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_type: Mapped[str] = mapped_column(String(32), nullable=False)  # morning/evening/night/etc
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    # end_time が start_time より小さい場合、翌日にまたぐ夜勤
    crosses_midnight: Mapped[bool] = mapped_column(default=False, nullable=False)

    shift: Mapped[Shift] = relationship("Shift", back_populates="assignments")
    employee: Mapped["Employee"] = relationship(  # noqa: F821
        "Employee", back_populates="assignments"
    )
