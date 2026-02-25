from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrchestratorMessageCreate(BaseModel):
    role: str = Field(..., min_length=1, max_length=20)   # "user" | "assistant"
    content: str = Field(..., min_length=1)


class OrchestratorMessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True