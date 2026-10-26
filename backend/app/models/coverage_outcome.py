"""人手不足の履歴（シフト生成ごとの各スロット実績）モデル。"""

from __future__ import annotations

from datetime import date, datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CoverageOutcome(Base):
    """シフト生成ごとの (日・拡張時) 単位の「必要人数 vs 実配置人数」の記録。

    人手不足(shortage = required − filled)を履歴として残し、曜日×時間帯の慢性不足の集計や
    人手不足予測(ML)の学習データにする。need(必要人数)は管理者が決める固定ルールなので学習対象では
    なく、ここに溜まる「どのスロットで配置が届かなかったか」を集計・学習する。
    月ごと1スナップショット（再生成時は当該 shift_id の行を全削除→再挿入）。
    """

    __tablename__ = "coverage_outcomes"
    __table_args__ = (
        UniqueConstraint("shift_id", "target_date", "hour", name="uq_coverage_outcome"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shift_id: Mapped[int] = mapped_column(
        ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 拡張時軸 0〜24+（HourlyStaffingRule.hour と同一軸。24=翌0:00, 25=翌1:00）。
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    # 必要人数の曜日区分（"weekday" / "weekend_or_holiday"）。集計・特徴量に使うため非正規化で保存。
    # ENUM ではなく文字列にして ENUM 型の再作成問題を避ける（分析用の付帯列のため）。
    day_category: Mapped[str] = mapped_column(String(24), nullable=False)
    # 曜日（月=0 … 日=6）。曜日×時間の集計・ML特徴量に使う。
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    # 祝日かどうか。繁忙や需要の季節性の手掛かりに使う。
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    required: Mapped[int] = mapped_column(Integer, nullable=False)
    filled: Mapped[int] = mapped_column(Integer, nullable=False)
    # 不足 = max(required − filled, 0)。保存時に確定させて入れる（集計の高速化）。
    shortage: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
