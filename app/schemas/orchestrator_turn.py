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


# ---------- CONTEXTO ENTENDIDO POR MINKABOT ----------

ResultType = Literal[
    "highlighted_document",
    "analysis_report",
    "executive_summary",
    "in_app_explanation",
    "dashboard_view",
]



class UIContextOut(BaseModel):
    task_type: str | None = None
    document_type: str | None = None
    analysis_goal: str | None = None
    input_source: str | None = None
    input_file_name: str | None = None
    uploaded_file_id: UUID | None = None
    file_uploaded: bool | None = None
    file_validation_status: str | None = None
    output_format: str | None = None  # transicional / legacy
    result_type: ResultType | None = None
    focus: list[str] = Field(default_factory=list)


# ---------- ESTADO DEL FLUJO ----------

InteractionMode = Literal["free_text", "hint_required", "guided_options", "review_edit"]

ActiveStep = Literal[
    "goal_intent",
    "document_type",
    "analysis_goal",
    "focus",
    "input_source",
    "file_intake",
    "result_type",
    "output_format",  # transicional / legacy
    "confirmation",
    "confirmation_edit",
]

ConfirmationState = Literal["none", "awaiting_confirmation", "editing"]


# ---------- TURN OUT ----------

class OrchestratorTurnOut(BaseModel):
    session_id: UUID

    # Mensajes creados
    user_message_id: UUID
    assistant_message_id: UUID
    reply: str
    created_at: datetime

    # Estado del flujo
    active_step: ActiveStep
    interaction_mode: InteractionMode
    confirmation_state: ConfirmationState = "none"

    # “Botón negro” (CTA)
    cta_ready: bool

    # Si se creó plan
    plan_created: bool
    plan_id: UUID | None = None
    plan_status: str | None = None

    # hints para UI
    ui_hints: UIHintsOut = Field(default_factory=UIHintsOut)

    # bullets para UI
    ui_bullets: UIBulletsOut | None = None

    # contexto según MinkaBot
    ui_context: UIContextOut | None = None

    class Config:
        from_attributes = True

class OrchestratorFileIntakeCompleteIn(BaseModel):
    uploaded_file_id: UUID


class OrchestratorFileIntakeCompleteOut(BaseModel):
    session_id: UUID
    assistant_message_id: UUID
    reply: str
    created_at: datetime

    active_step: ActiveStep
    interaction_mode: InteractionMode
    confirmation_state: ConfirmationState = "none"

    cta_ready: bool
    plan_created: bool
    plan_id: UUID | None = None
    plan_status: str | None = None

    ui_hints: UIHintsOut = Field(default_factory=UIHintsOut)
    ui_bullets: UIBulletsOut | None = None
    ui_context: UIContextOut | None = None

    class Config:
        from_attributes = True