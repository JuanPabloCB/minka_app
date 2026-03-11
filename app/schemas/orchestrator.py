# app/schemas/orchestrator.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OrchestratorMessageIn(BaseModel):
    session_id: UUID
    content: str


UIHintType = Literal["quick_replies", "tool_select", "actions"]


class UIHintOption(BaseModel):
    key: str
    label: str
    value: str | None = None
    enabled: bool = True
    reason: str | None = None


class UIHint(BaseModel):
    type: UIHintType
    title: str | None = None
    options: list[UIHintOption] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class UIHintsOut(BaseModel):
    hints: list[UIHint] = Field(default_factory=list)


class OrchestratorMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    reply: str
    created_at: datetime

    # NUEVO
    ui_hints: UIHintsOut = Field(default_factory=UIHintsOut)