from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, Field


class OrchestratorMessageCreate(BaseModel):
    role: str = Field(..., min_length=1, max_length=20)
    content: str = Field(..., min_length=1)


class OrchestratorMessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True