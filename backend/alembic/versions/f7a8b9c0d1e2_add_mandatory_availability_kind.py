"""add mandatory to availability_kind enum

確定出勤(mandatory)を具体日付の availability 種別として追加(ADR-0009 改訂)。
シフト表と同じカレンダー上で登録し、生成時は「必ず1シフト」制約になる。

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-09-14 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Postgres の enum への値追加はトランザクション外で実行する必要がある。
    op.execute("COMMIT")
    op.execute("ALTER TYPE availability_kind ADD VALUE IF NOT EXISTS 'mandatory'")


def downgrade() -> None:
    # Postgres は enum 値の削除を直接サポートしないため no-op。
    pass
