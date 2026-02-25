# app/schemas/sessions.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    user_id: str | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime