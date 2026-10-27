"""add capacity features to coverage_outcomes

Revision ID: e2a3b4c5d6f7
Revises: d1f2a3b4c5e6
Create Date: 2026-10-26 01:00:00.000000

人手不足予測（ADR-0013）の特徴量強化。各スロットに生成時点の容量を記録する:
active_employees（有効従業員数）と available_employees（その時間に入れる従業員数）。
need に対して容量が足りないほど不足が起きやすい、という関係を学習に使う。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2a3b4c5d6f7"
down_revision: str | None = "d1f2a3b4c5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "coverage_outcomes",
        sa.Column(
            "active_employees", sa.Integer, nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "coverage_outcomes",
        sa.Column(
            "available_employees", sa.Integer, nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    op.drop_column("coverage_outcomes", "available_employees")
    op.drop_column("coverage_outcomes", "active_employees")
