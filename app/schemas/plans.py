# app/schemas/plans.py
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlanStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    step_index: int
    title: str
    status: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class PlanCreateDraftIn(BaseModel):
    session_id: UUID
    title: str = Field(default="", max_length=200)


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    status: str
    title: str

    ui_state: str
    selected_analysts: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime


class PlanDraftOut(BaseModel):
    plan: PlanOut
    steps: list[PlanStepOut]
    created_new: bool


class PlanReadyOut(BaseModel):
    plan_id: UUID
    status: str
    ui_state: str


class PlanWithStepsOut(BaseModel):
    plan: PlanOut
    steps: list[PlanStepOut]


class PlanListOut(BaseModel):
    plans: list[PlanOut]


class PlanSetUIStateIn(BaseModel):
    ui_state: str = Field(min_length=1, max_length=20)


class PlanSetSelectedAnalystsIn(BaseModel):
    selected_analysts: list[dict[str, Any]] = Field(default_factory=list)


class PlanMetaPatchIn(BaseModel):
    patch: dict[str, Any] = Field(default_factory=dict)