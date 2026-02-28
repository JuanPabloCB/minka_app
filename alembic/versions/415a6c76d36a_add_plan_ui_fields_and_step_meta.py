"""add plan ui fields and step meta

Revision ID: 415a6c76d36a
Revises: 449e74bcbb94
Create Date: 2026-02-27 03:29:35.569728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "415a6c76d36a"
down_revision: Union[str, None] = "449e74bcbb94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) plan_steps.meta (JSONB NOT NULL) + updated_at
    op.add_column(
        "plan_steps",
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "plan_steps",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 2) Unique constraint (plan_id, step_index)
    op.create_unique_constraint(
        "uq_plan_steps_plan_id_step_index",
        "plan_steps",
        ["plan_id", "step_index"],
    )

    # 3) plans.ui_state (NOT NULL) + selected_analysts (JSONB NOT NULL) + meta (JSONB NOT NULL) + updated_at
    op.add_column(
        "plans",
        sa.Column(
            "ui_state",
            sa.String(length=20),
            nullable=False,
            server_default="configuring",
        ),
    )
    op.add_column(
        "plans",
        sa.Column(
            "selected_analysts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "plans",
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "plans",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ✅ Recomendado: remover server_default después de backfill
    # (para que tu app sea la que controla valores nuevos)
    op.alter_column("plan_steps", "meta", server_default=None)
    op.alter_column("plans", "ui_state", server_default=None)
    op.alter_column("plans", "selected_analysts", server_default=None)
    op.alter_column("plans", "meta", server_default=None)


def downgrade() -> None:
    # Revertir en orden inverso
    op.drop_column("plans", "updated_at")
    op.drop_column("plans", "meta")
    op.drop_column("plans", "selected_analysts")
    op.drop_column("plans", "ui_state")

    op.drop_constraint("uq_plan_steps_plan_id_step_index", "plan_steps", type_="unique")
    op.drop_column("plan_steps", "updated_at")
    op.drop_column("plan_steps", "meta")