"""add analysts runs and artifacts

Revision ID: 9a1b2c3d4e5f
Revises: 197e354137eb
Create Date: 2026-03-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9a1b2c3d4e5f"
down_revision: Union[str, None] = "197e354137eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # analysts
    # ------------------------------------------------------------------
    op.create_table(
        "analysts",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("capabilities", sa.Text(), nullable=True),
        sa.Column("supports_inputs", sa.Text(), nullable=True),
        sa.Column("supports_outputs", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("idx_analysts_enabled", "analysts", ["enabled"])
    op.create_index("idx_analysts_updated", "analysts", ["updated_at"])

    op.execute(
        """
        INSERT INTO analysts (
            id, name, enabled, capabilities, supports_inputs, supports_outputs
        )
        VALUES (
            'legal_analyst',
            'Analista Legal',
            true,
            'contract_review,critical_clause_detection,risk_prioritization,practical_interpretation',
            'pdf,docx,txt',
            'json,marked_contract,summary'
        )
        ON CONFLICT (id) DO NOTHING
        """
    )

    # ------------------------------------------------------------------
    # analyst_runs
    # OJO: plan_steps.id y plans.id en tu DB son UUID, no CHAR(36)
    # ------------------------------------------------------------------
    op.create_table(
        "analyst_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("plan_step_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "awaiting_input",
                "in_progress",
                "done",
                "error",
                name="analyst_run_status_enum",
            ),
            nullable=False,
            server_default="awaiting_input",
        ),
        sa.Column("current_step", sa.Integer(), nullable=True),
        sa.Column(
            "run_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("audit_log", sa.Text(), nullable=True),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["plan_step_id"], ["plan_steps.id"], name="fk_analyst_runs_plan_step_id"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], name="fk_analyst_runs_plan_id"),
    )

    op.create_index("idx_runs_step", "analyst_runs", ["plan_step_id"])
    op.create_index("idx_runs_plan", "analyst_runs", ["plan_id"])
    op.create_index("idx_runs_status", "analyst_runs", ["status"])
    op.create_index("idx_runs_updated", "analyst_runs", ["updated_at"])

    # ------------------------------------------------------------------
    # artifacts
    # OJO: owner_id también lo dejamos UUID para mantener consistencia
    # ------------------------------------------------------------------
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column(
            "owner_type",
            sa.Enum(
                "session",
                "plan",
                "plan_step",
                "analyst_run",
                "automation",
                "automation_run",
                name="artifact_owner_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "context",
                "input",
                "output",
                "intermediate",
                name="artifact_kind_enum",
            ),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column(
            "storage_provider",
            sa.Enum("supabase", "s3", "local", name="artifact_storage_provider_enum"),
            nullable=False,
            server_default="local",
        ),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("idx_artifacts_owner", "artifacts", ["owner_type", "owner_id"])
    op.create_index("idx_artifacts_user", "artifacts", ["user_id"])
    op.create_index("idx_artifacts_kind", "artifacts", ["kind"])
    op.create_index("idx_artifacts_created", "artifacts", ["created_at"])
    op.create_index("idx_artifacts_sha256", "artifacts", ["sha256"])


def downgrade() -> None:
    op.drop_index("idx_artifacts_sha256", table_name="artifacts")
    op.drop_index("idx_artifacts_created", table_name="artifacts")
    op.drop_index("idx_artifacts_kind", table_name="artifacts")
    op.drop_index("idx_artifacts_user", table_name="artifacts")
    op.drop_index("idx_artifacts_owner", table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index("idx_runs_updated", table_name="analyst_runs")
    op.drop_index("idx_runs_status", table_name="analyst_runs")
    op.drop_index("idx_runs_plan", table_name="analyst_runs")
    op.drop_index("idx_runs_step", table_name="analyst_runs")
    op.drop_table("analyst_runs")

    op.drop_index("idx_analysts_updated", table_name="analysts")
    op.drop_index("idx_analysts_enabled", table_name="analysts")
    op.drop_table("analysts")

    op.execute("DROP TYPE IF EXISTS artifact_storage_provider_enum")
    op.execute("DROP TYPE IF EXISTS artifact_kind_enum")
    op.execute("DROP TYPE IF EXISTS artifact_owner_type_enum")
    op.execute("DROP TYPE IF EXISTS analyst_run_status_enum")