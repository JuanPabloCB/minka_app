"""merge alembic heads

Revision ID: 8f04c27700f7
Revises: 22616a328992, ae2918a404b7
Create Date: 2026-03-28 00:14:27.629536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f04c27700f7'
down_revision: Union[str, None] = ('22616a328992', 'ae2918a404b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
