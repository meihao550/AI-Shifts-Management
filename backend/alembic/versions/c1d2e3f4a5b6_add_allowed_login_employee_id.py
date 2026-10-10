"""add allowed_logins.employee_id (ログイン↔従業員の紐付け)

種別が従業員のログインを、どの従業員レコードに紐付けるかを保持する。
ログイン時に User.employee_id へ同期され、ダッシュボードの予定給与表示に使う。

Revision ID: c1d2e3f4a5b6
Revises: b9c0d1e2f3a4
Create Date: 2026-10-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "allowed_logins",
        sa.Column("employee_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_allowed_logins_employee_id",
        "allowed_logins",
        "employees",
        ["employee_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_allowed_logins_employee_id", "allowed_logins", type_="foreignkey"
    )
    op.drop_column("allowed_logins", "employee_id")
