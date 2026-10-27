"""add coverage_outcomes

Revision ID: d1f2a3b4c5e6
Revises: c1d2e3f4a5b6
Create Date: 2026-10-26 00:00:00.000000

人手不足予測（ADR-0013）のための履歴テーブル。シフト生成のたびに各 (日・拡張時) の
必要人数(required)・実配置(filled)・不足(shortage) を記録し、曜日×時間の慢性不足の集計や
ML 学習データにする。月ごと1スナップショット（再生成時は当該 shift_id を全削除→再挿入）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1f2a3b4c5e6"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "coverage_outcomes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "shift_id",
            sa.Integer,
            sa.ForeignKey("shifts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_date", sa.Date, nullable=False),
        sa.Column("hour", sa.Integer, nullable=False),
        sa.Column("day_category", sa.String(24), nullable=False),
        sa.Column("weekday", sa.Integer, nullable=False),
        sa.Column("is_holiday", sa.Boolean, nullable=False),
        sa.Column("required", sa.Integer, nullable=False),
        sa.Column("filled", sa.Integer, nullable=False),
        sa.Column("shortage", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "shift_id", "target_date", "hour", name="uq_coverage_outcome"
        ),
    )
    op.create_index(
        "ix_coverage_outcomes_shift_id", "coverage_outcomes", ["shift_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_coverage_outcomes_shift_id", table_name="coverage_outcomes")
    op.drop_table("coverage_outcomes")
