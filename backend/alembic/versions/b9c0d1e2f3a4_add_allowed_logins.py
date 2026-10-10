"""add allowed_logins (ログイン許可リスト) + seed 初期管理者

許可リストに載っている email だけ OAuth ログインできる(ADR-0010)。
初期管理者として ziyin550@gmail.com を登録する。

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-09-16 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9c0d1e2f3a4"
down_revision: str | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 既存の user_role enum を再利用する（新規作成しない）。
user_role = postgresql.ENUM("admin", "employee", name="user_role", create_type=False)


def upgrade() -> None:
    op.create_table(
        "allowed_logins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="employee"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_allowed_logins_email"),
    )
    op.create_index("ix_allowed_logins_email", "allowed_logins", ["email"])
    # 初期管理者を投入。
    op.execute(
        "INSERT INTO allowed_logins (name, email, role) "
        "VALUES ('管理者', 'ziyin550@gmail.com', 'admin')"
    )


def downgrade() -> None:
    op.drop_index("ix_allowed_logins_email", table_name="allowed_logins")
    op.drop_table("allowed_logins")
