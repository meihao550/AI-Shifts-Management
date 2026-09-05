"""Employee & availability models."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EmployeeRole(StrEnum):
    admin = "admin"
    employee = "employee"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 交通費 (JPY / day)
    transport_cost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 時給 (JPY)
    hourly_wage: Mapped[int] = mapped_column(Integer, default=1100, nullable=False)
    # メインで入るシフト種別 (morning/evening/night 等)
    main_shift_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # メインシフトを絶対遵守（ピン）。True ならメイン区分のみに配置するハード制約にする
    main_shift_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Wワーク（掛け持ち）従業員か。True なら基本+Wワーク専用パターンの両方に入れる。
    # False（通常従業員）は基本パターンのみ（Wワーク専用パターンには配置しない）。
    is_dual_worker: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 週に何回入るか
    weekly_shifts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    # 有給
    paid_leave_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 普段入れる時間帯（1時間単位, 0〜24）。両方 None なら制限なし。
    # 終了 <= 開始 は翌日跨ぎ扱い（例 18-2 = 18:00〜翌2:00）。この窓に完全に収まる
    # パターンのみ生成時に配置する（ハード制約）。
    available_start_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_end_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[EmployeeRole] = mapped_column(
        SAEnum(EmployeeRole, name="employee_role"),
        default=EmployeeRole.employee,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User | None] = relationship(  # noqa: F821
        "User", back_populates="employee", uselist=False
    )
    availabilities: Mapped[list[EmployeeAvailability]] = relationship(
        "EmployeeAvailability",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list[ShiftAssignment]] = relationship(  # noqa: F821
        "ShiftAssignment",
        back_populates="employee",
    )


class AvailabilityKind(StrEnum):
    unavailable = "unavailable"  # 絶対勤務不可
    preferred = "preferred"  # 入りたい
    paid_leave = "paid_leave"  # 有給休暇（勤務不可扱い＋人件費に日額を加算）


class EmployeeAvailability(Base):
    __tablename__ = "employee_availabilities"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "target_date", "shift_type", "kind", name="uq_availability"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[AvailabilityKind] = mapped_column(
        SAEnum(AvailabilityKind, name="availability_kind"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    employee: Mapped[Employee] = relationship("Employee", back_populates="availabilities")
