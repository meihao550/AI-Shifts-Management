"""add employee_fixed_schedules

従業員ごとの固定カレンダー(曜日パターン)。毎月流用する(ADR-0007)。
day_of_week は date.weekday() 準拠(月=0..日=6)。status は work/off。

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-14 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employee_fixed_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("work", "off", name="fixed_schedule_status"),
            nullable=False,
        ),
        sa.UniqueConstraint("employee_id", "day_of_week", name="uq_fixed_schedule"),
    )


def downgrade() -> None:
    op.drop_table("employee_fixed_schedules")
    sa.Enum(name="fixed_schedule_status").drop(op.get_bind(), checkfirst=True)
