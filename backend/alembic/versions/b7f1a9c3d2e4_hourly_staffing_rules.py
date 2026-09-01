"""replace staffing_rules with hourly_staffing_rules

Revision ID: b7f1a9c3d2e4
Revises: caaa2cd6e846
Create Date: 2026-08-30 00:00:00.000000

時間カバレッジ方式（要件書§13）への移行。区分別（朝/夜/深夜）の必要人数
テーブル staffing_rules を廃止し、1時間ごとの必要人数を持つ
hourly_staffing_rules を導入する。day_category ENUM は既存のものを再利用する。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f1a9c3d2e4"
down_revision: str | None = "caaa2cd6e846"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 既存の day_category ENUM を再利用する（CREATE TYPE を再実行しない）。
_day_category = postgresql.ENUM(
    "weekday", "weekend_or_holiday", name="day_category", create_type=False
)


def upgrade() -> None:
    op.drop_table("staffing_rules")
    op.create_table(
        "hourly_staffing_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("day_category", _day_category, nullable=False),
        sa.Column("hour", sa.Integer, nullable=False),
        sa.Column("required", sa.Integer, nullable=False),
        sa.UniqueConstraint("day_category", "hour", name="uq_hourly_staffing_rule"),
    )


def downgrade() -> None:
    op.drop_table("hourly_staffing_rules")
    op.create_table(
        "staffing_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("day_category", _day_category, nullable=False),
        sa.Column("shift_category", sa.String(16), nullable=False),
        sa.Column("required", sa.Integer, nullable=False),
        sa.UniqueConstraint("day_category", "shift_category", name="uq_staffing_rule"),
    )
