from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LegalAnalystExecuteRequest(BaseModel):
    goal_type: str = Field(..., min_length=1)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    assigned_macro_steps: List[Dict[str, Any]] = Field(default_factory=list)


class MacroStepIn(BaseModel):
    id: str | None = None
    title: str | None = None
    description: str | None = None
    expected_output: str | None = None


class StepChatScopeOut(BaseModel):
    mode: str
    allowed_topics: list[str] = Field(default_factory=list)


class StepInitialMessageOut(BaseModel):
    id: str
    type: str
    content: str
    animate: bool = True


class StepRenderBlockOut(BaseModel):
    id: str
    type: str
    label: str | None = None
    accepted_formats: list[str] = Field(default_factory=list)


class StepUiDefinitionOut(BaseModel):
    step_id: str
    title: str
    chat_scope: StepChatScopeOut
    initial_messages: list[StepInitialMessageOut] = Field(default_factory=list)
    render_blocks: list[StepRenderBlockOut] = Field(default_factory=list)


class StepResultOut(BaseModel):
    step_id: str
    status: str
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RuntimeContextOut(BaseModel):
    analyst_id: str
    goal_type: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    shared_state: dict[str, Any] = Field(default_factory=dict)
    step_results: list[StepResultOut] = Field(default_factory=list)


class LegalAnalystExecuteResponse(BaseModel):
    analyst_id: str
    goal_type: str
    selected_steps: List[str]
    ordered_steps: List[str]
    planning_reasoning: List[str]
    dependency_errors: List[str]
    missing_dependencies: List[str]
    runtime_context: Optional[Dict[str, Any]] = None
    step_ui_map: dict[str, StepUiDefinitionOut] = Field(default_factory=dict)


class UploadContractResponse(BaseModel):
    ok: bool
    run_id: str
    artifact_id: str
    document_id: str
    filename: str
    content_type: str
    size_bytes: int
    size_label: str
    page_count: int | None = None
    validation_status: str
    is_contract_candidate: bool
    document_type_guess: str
    text_length: int
    message: str
    storage_path: str
    current_macro_step_id: str | None = None
    current_macro_step_title: str | None = None
    selected_micro_steps: list[str] = Field(default_factory=list)
    current_micro_step: str | None = None


class LegalAnalystStepChatRequest(BaseModel):
    step_id: str = Field(..., min_length=1)
    user_message: str = Field(..., min_length=1)
    goal_type: str | None = None
    document_id: str | None = None
    filename: str | None = None
    step_output: dict[str, Any] = Field(default_factory=dict)


class LegalAnalystStepChatResponse(BaseModel):
    step_id: str
    reply: str
    render_blocks: list[StepRenderBlockOut] = Field(default_factory=list)


class DetectFindingsRequest(BaseModel):
    run_id: str
    macro_step_id: str | None = None
    macro_step_title: str | None = None
    detection_mode: str = Field(default="all_clauses")
    clause_targets: list[str] = Field(default_factory=lambda: ["all"])
    finding_targets: list[str] = Field(default_factory=lambda: ["clauses"])

class FindingOut(BaseModel):
    finding_id: str
    title: str
    category: str
    confidence: float
    excerpt: str
    reason: str
    segment_id: str | None = None
    title_guess: str | None = None


class DetectFindingsResponse(BaseModel):
    ok: bool
    run_id: str
    macro_step_id: str | None = None
    macro_step_title: str | None = None
    micro_step: str

    detection_mode: str
    clause_targets: list[str] = Field(default_factory=list)
    finding_targets: list[str] = Field(default_factory=list)

    total_findings: int
    findings: list[FindingOut] = Field(default_factory=list)

    formal_findings: list[FindingOut] = Field(default_factory=list)
    functional_findings: list[FindingOut] = Field(default_factory=list)
    atomic_findings: list[FindingOut] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    message: str