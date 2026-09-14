"""add insurance_type to employees

保険区分(social/employment/none)をマスタ属性として追加(ADR-0006)。
月間実働時間のハード制約に使う。既存行は 'none' でバックフィル。

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-09-14 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "insurance_type",
            sa.String(16),
            nullable=False,
            server_default="none",
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "insurance_type")
