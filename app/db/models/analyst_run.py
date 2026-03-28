from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Enum, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalystRun(Base):
    __tablename__ = "analyst_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # OJO:
    # Este campo lo seguimos usando por compatibilidad,
    # pero semánticamente representa el macro step visible
    # al que esta corrida queda anclada.
    plan_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plan_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    status: Mapped[str] = mapped_column(
        Enum(
            "awaiting_input",
            "in_progress",
            "done",
            "error",
            name="analyst_run_status_enum",
        ),
        nullable=False,
        default="awaiting_input",
    )

    current_step: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Aquí vive el runtime real:
    # assigned_macro_steps, selected_micro_steps, current_micro_step, etc.
    run_context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    audit_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )