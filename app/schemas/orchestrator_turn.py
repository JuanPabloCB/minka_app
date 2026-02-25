from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class OrchestratorTurnIn(BaseModel):
    content: str = Field(..., min_length=1)


class OrchestratorTurnOut(BaseModel):
    session_id: UUID

    # Mensajes creados
    user_message_id: UUID
    assistant_message_id: UUID
    reply: str
    created_at: datetime

    # “Botón negro” (CTA)
    cta_ready: bool

    # Si se creó plan
    plan_created: bool
    plan_id: UUID | None = None
    plan_status: str | None = None

    class Config:
        from_attributes = True