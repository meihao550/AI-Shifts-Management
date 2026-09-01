"""add paid_leave to availability_kind enum

Revision ID: d4a7b2e9f6c1
Revises: c8e2f4a6d1b9
Create Date: 2026-09-01 00:00:00.000000

有給休暇を availabilities.kind の選択肢に追加する。有給日は勤務不可扱いにしつつ、
人件費に「有給1日あたりの金額」を加算する（要件F-3 / 9.1）。
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a7b2e9f6c1"
down_revision: str | None = "c8e2f4a6d1b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL では ENUM への値追加はトランザクション外で行う必要がある。
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE availability_kind ADD VALUE IF NOT EXISTS 'paid_leave'")


def downgrade() -> None:
    # PostgreSQL は ENUM 値の削除をサポートしないため no-op とする。
    pass
