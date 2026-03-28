"""merge analysts artifacts with repaired meta

Revision ID: ae2918a404b7
Revises: 9a1b2c3d4e5f, f2f01c221b30
Create Date: 2026-03-23 16:12:46.673898

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae2918a404b7'
down_revision: Union[str, None] = ('9a1b2c3d4e5f', 'f2f01c221b30')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
