"""add meta to orchestrator_messages

Revision ID: 197e354137eb
Revises: 415a6c76d36a
Create Date: 2026-03-11 18:18:32.387030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "197e354137eb"
down_revision: Union[str, None] = "415a6c76d36a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orchestrator_messages",
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.alter_column("orchestrator_messages", "meta", server_default=None)


def downgrade() -> None:
    op.drop_column("orchestrator_messages", "meta")