"""drop is_basic from shift_patterns

基本/Wワークのパターン区別を廃止し、全パターンを1プールに統合(ADR-0004)。
配置制限は勤務可能時間帯(1時間窓)のみ。

Revision ID: b3c4d5e6f7a8
Revises: a9b8c7d6e5f4
Create Date: 2026-09-07 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a9b8c7d6e5f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("shift_patterns", "is_basic")


def downgrade() -> None:
    op.add_column(
        "shift_patterns",
        sa.Column(
            "is_basic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
