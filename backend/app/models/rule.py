"""Shift pattern definitions & staffing rules."""

from __future__ import annotations

from datetime import time
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DayCategory(StrEnum):
    weekday = "weekday"
    weekend_or_holiday = "weekend_or_holiday"


class ShiftPattern(Base):
    """A shift pattern like 9-17 (morning) or 17-1 (evening)."""

    __tablename__ = "shift_patterns"
    __table_args__ = (UniqueConstraint("code", name="uq_shift_pattern_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. "morning", "12-20"
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_basic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # morning/evening/night: high-level bucket used for staffing constraints
    category: Mapped[str] = mapped_column(String(16), nullable=False)


class HourlyStaffingRule(Base):
    """Required number of workers per (day category, hour).

    時間カバレッジ方式（要件書§13）: 必要人数を「1時間ごと」に持つ。
    hour は 0〜24 の拡張時軸（24=翌0:00, 25=翌1:00 ...）で、深夜跨ぎの
    シフトも同じ営業日として扱えるようにする（要件書§12.2 の 25:00 表記に整合）。
    """

    __tablename__ = "hourly_staffing_rules"
    __table_args__ = (
        UniqueConstraint("day_category", "hour", name="uq_hourly_staffing_rule"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_category: Mapped[DayCategory] = mapped_column(
        SAEnum(DayCategory, name="day_category"), nullable=False
    )
    # 拡張時軸上の「時」。例: 9 は 9:00-10:00 を表す。24=0:00, 25=1:00。
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    required: Mapped[int] = mapped_column(Integer, nullable=False)
