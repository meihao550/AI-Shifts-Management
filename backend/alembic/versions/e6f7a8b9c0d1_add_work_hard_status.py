"""add work_hard to fixed_schedule_status enum

確定出勤(work_hard)を固定カレンダーの状態に追加(ADR-0009)。
生成時に mandatory(必ず1シフト)として展開する。

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-09-14 11:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Postgres の enum に値を追加する（ADD VALUE はトランザクション外で実行する必要がある）。
    op.execute("COMMIT")
    op.execute("ALTER TYPE fixed_schedule_status ADD VALUE IF NOT EXISTS 'work_hard'")


def downgrade() -> None:
    # Postgres は enum 値の削除を直接サポートしないため、ダウングレードは no-op とする。
    pass
