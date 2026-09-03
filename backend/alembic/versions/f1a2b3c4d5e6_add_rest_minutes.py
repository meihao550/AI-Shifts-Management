"""add rest_minutes to shift_patterns

Revision ID: f1a2b3c4d5e6
Revises: d4a7b2e9f6c1
Create Date: 2026-09-03 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "d4a7b2e9f6c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 既存行にも値が要るので server_default="0"（モデルの default=0 に対応）
    op.add_column(
        "shift_patterns",
        sa.Column("rest_minutes", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("shift_patterns", "rest_minutes")
