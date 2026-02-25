# app/schemas/orchestrator.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class OrchestratorMessageIn(BaseModel):
    session_id: UUID
    content: str


class OrchestratorMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime