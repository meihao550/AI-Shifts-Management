"""add available_start_hour / available_end_hour to employees

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-09-05 03:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULL = 制限なし（既存従業員は従来どおり全時間に配置可）。
    op.add_column("employees", sa.Column("available_start_hour", sa.Integer(), nullable=True))
    op.add_column("employees", sa.Column("available_end_hour", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "available_end_hour")
    op.drop_column("employees", "available_start_hour")
