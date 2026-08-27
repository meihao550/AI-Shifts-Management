"""pair constraint

Revision ID: 5b2c4d86971c
Revises: 0001
Create Date: 2026-08-21 05:39:08.554902

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b2c4d86971c"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employee_pair_constraints",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "employee_a_id",
            sa.Integer,
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "employee_b_id",
            sa.Integer,
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("employee_pair_constraints")
