"""drop employee_fixed_schedules (曜日テンプレ廃止)

固定カレンダーを曜日テンプレ方式から、シフト表と共有する具体日付の availability に
統一したため、専用テーブルと enum を削除する(ADR-0007 改訂)。

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-09-14 12:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("employee_fixed_schedules")
    sa.Enum(name="fixed_schedule_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    status = sa.Enum("work", "work_hard", "off", name="fixed_schedule_status")
    status.create(op.get_bind(), checkfirst=True)
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
        sa.Column("status", status, nullable=False),
        sa.UniqueConstraint("employee_id", "day_of_week", name="uq_fixed_schedule"),
    )
