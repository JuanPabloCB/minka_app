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

class AnalystActionStepOut(BaseModel):
    key: str
    label: str
    status: str
    estimated_minutes: int


class SourceStepAssignmentOut(BaseModel):
    step_index: int
    title: str
    analyst_key: str
    analyst_label: str


class ExecutionRouteStepOut(BaseModel):
    index: int
    analyst_key: str
    analyst_label: str
    status: str
    estimated_minutes: int
    task_titles: list[str] = Field(default_factory=list)
    source_step_indexes: list[int] = Field(default_factory=list)
    source_step_assignments: list[SourceStepAssignmentOut] = Field(default_factory=list)
    analyst_actions: list[AnalystActionStepOut] = Field(default_factory=list)
    expected_output: str = Field(default="")


class ExecutionRouteOut(BaseModel):
    plan: PlanOut
    progress_percent: int
    execution_status: str
    estimated_total_minutes: int
    execution_steps: list[ExecutionRouteStepOut] = Field(default_factory=list)

class PlanListOut(BaseModel):
    plans: list[PlanOut]


class PlanSetUIStateIn(BaseModel):
    ui_state: str = Field(min_length=1, max_length=20)


class PlanSetSelectedAnalystsIn(BaseModel):
    selected_analysts: list[dict[str, Any]] = Field(default_factory=list)


class PlanMetaPatchIn(BaseModel):
    patch: dict[str, Any] = Field(default_factory=dict)