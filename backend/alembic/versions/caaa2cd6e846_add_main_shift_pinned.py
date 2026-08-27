"""add main_shift_pinned

Revision ID: caaa2cd6e846
Revises: e3677873f649
Create Date: 2026-08-27 05:13:01.434974

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "caaa2cd6e846"
down_revision: str | None = "e3677873f649"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "main_shift_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "main_shift_pinned")
