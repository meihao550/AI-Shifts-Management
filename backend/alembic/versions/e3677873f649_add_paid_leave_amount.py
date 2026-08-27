"""add paid_leave_amount

Revision ID: e3677873f649
Revises: 5b2c4d86971c
Create Date: 2026-08-24 17:08:53.224733

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3677873f649"
down_revision: str | None = "5b2c4d86971c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 既存行にも値が要るので server_default="0"（モデルの default=0 に対応）
    op.add_column(
        "employees",
        sa.Column("paid_leave_amount", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("employees", "paid_leave_amount")
