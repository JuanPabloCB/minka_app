from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    owner_type: Mapped[str] = mapped_column(
        Enum(
            "session",
            "plan",
            "plan_step",
            "analyst_run",
            "automation",
            "automation_run",
            name="artifact_owner_type_enum",
        ),
        nullable=False,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    kind: Mapped[str] = mapped_column(
        Enum(
            "context",
            "input",
            "output",
            "intermediate",
            name="artifact_kind_enum",
        ),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(String(512), nullable=False)

    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)

    storage_provider: Mapped[str] = mapped_column(
        Enum("supabase", "s3", "local", name="artifact_storage_provider_enum"),
        nullable=False,
        default="local",
    )

    storage_path: Mapped[str] = mapped_column(Text, nullable=False)

    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Columna real en DB: metadata
    # atributo Python: meta
    meta: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )