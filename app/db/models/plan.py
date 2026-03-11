# app/db/models/plan.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orchestrator_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Estados del plan (macro): draft -> ready -> in_progress -> done/error
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Título visible (ej: "Generar resumen de contrato")
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    # Estado UI (para tu pantalla: "Configurando" / "Listo")
    # No es “lógico de negocio”; es un hint de interfaz.
    ui_state: Mapped[str] = mapped_column(String(20), nullable=False, default="configuring")

    # Preparado: analistas seleccionados por el orquestador (sin crear tabla extra todavía)
    # Ejemplo: [{"analyst_key":"legal_v1","reason":"..."}]
    selected_analysts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Preparado: metadata flexible (por ejemplo: output_type, restricciones, etc.)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    session = relationship("OrchestratorSession", back_populates="plans")

    # PlanStep existe aunque no lo muestres en UI: es “plan interno”
    steps = relationship(
        "PlanStep",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanStep.step_index",
    )