from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any, Literal

from pydantic import BaseModel, Field


class OrchestratorTurnIn(BaseModel):
    content: str = Field(..., min_length=1)


# ---------- UI HINTS (botones / sugerencias) ----------

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


# ---------- UI BULLETS (lista / timeline) ----------

UIBulletsVariant = Literal["timeline", "bullets"]

class UIBulletItem(BaseModel):
    key: str
    label: str

class UIBulletsOut(BaseModel):
    title: str | None = None
    variant: UIBulletsVariant = "timeline"
    items: list[UIBulletItem] = Field(default_factory=list)


# ---------- TURN OUT ----------

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

    # NUEVO: hints para UI (botones)
    ui_hints: UIHintsOut = Field(default_factory=UIHintsOut)

    # NUEVO: bullets para UI (lista / timeline)
    ui_bullets: UIBulletsOut | None = None

    class Config:
        from_attributes = True