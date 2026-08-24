"""add paid_leave_amount

Revision ID: e3677873f649
Revises: 0001
Create Date: 2026-08-24 17:08:53.224733

"""
from collections.abc import Sequence
from typing import Union

#from alembic import op
#import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3677873f649'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
