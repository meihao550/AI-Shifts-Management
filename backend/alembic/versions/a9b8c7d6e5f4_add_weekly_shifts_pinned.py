"""add weekly_shifts_pinned to employees

週回数を完全週でちょうどのハード制約にするフラグ(ADR-0003)。
既存従業員は OFF のまま（server_default=false でバックフィル）。新規従業員は
モデルの Python 側 default=True により ORM INSERT 時に True になる。

Revision ID: a9b8c7d6e5f4
Revises: e1d2c3b4a5f6
Create Date: 2026-09-07 08:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: str | None = "e1d2c3b4a5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "weekly_shifts_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "weekly_shifts_pinned")
