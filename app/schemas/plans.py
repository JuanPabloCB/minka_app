# app/schemas/plans.py
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import List

class PlanStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    plan_id: UUID
    step_index: int
    title: str
    status: str

class PlanCreateDraftIn(BaseModel):
    session_id: UUID
    title: str = Field(default="", max_length=200)

class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    status: str
    title: str

class PlanDraftOut(BaseModel):
    plan: PlanOut
    steps: List[PlanStepOut]

class PlanReadyOut(BaseModel):
    plan_id: UUID
    status: str

class PlanWithStepsOut(BaseModel):
    plan: PlanOut
    steps: List[PlanStepOut]

class PlanListOut(BaseModel):
    plans: List[PlanOut]