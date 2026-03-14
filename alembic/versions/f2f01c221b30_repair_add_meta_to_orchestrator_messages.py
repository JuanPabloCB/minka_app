"""repair add meta to orchestrator_messages

Revision ID: f2f01c221b30
Revises: 197e354137eb
Create Date: 2026-03-11 18:45:12.707107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2f01c221b30"
down_revision: Union[str, None] = "197e354137eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'orchestrator_messages'
                  AND column_name = 'meta'
            ) THEN
                ALTER TABLE orchestrator_messages
                ADD COLUMN meta jsonb NOT NULL DEFAULT '{}'::jsonb;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        ALTER TABLE orchestrator_messages
        ALTER COLUMN meta DROP DEFAULT;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'orchestrator_messages'
                  AND column_name = 'meta'
            ) THEN
                ALTER TABLE orchestrator_messages
                DROP COLUMN meta;
            END IF;
        END
        $$;
        """
    )