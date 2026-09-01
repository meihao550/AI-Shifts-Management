"""add is_dual_worker to employees

Revision ID: c8e2f4a6d1b9
Revises: b7f1a9c3d2e4
Create Date: 2026-09-01 00:00:00.000000

Wワーク（掛け持ち）従業員の判定フラグを追加する。True の従業員は基本+Wワーク専用
パターンの両方に配置でき、False（通常従業員）は基本パターンのみに配置される。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8e2f4a6d1b9"
down_revision: str | None = "b7f1a9c3d2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "is_dual_worker",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "is_dual_worker")
