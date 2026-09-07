"""drop main_shift_type / main_shift_pinned from employees

メインシフト区分(朝/夜/深夜)を廃止し、配置制御を勤務可能時間帯に一本化(ADR-0002)。

Revision ID: e1d2c3b4a5f6
Revises: b2c3d4e5f6a7
Create Date: 2026-09-07 08:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1d2c3b4a5f6"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("employees", "main_shift_pinned")
    op.drop_column("employees", "main_shift_type")


def downgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("main_shift_type", sa.String(32), nullable=True),
    )
    op.add_column(
        "employees",
        sa.Column(
            "main_shift_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
