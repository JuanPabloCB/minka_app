from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ClauseClassification(BaseModel):
    type: Literal[
        "payment",
        "termination",
        "liability",
        "confidentiality",
        "intellectual_property",
        "governing_law",
        "dispute_resolution",
        "force_majeure",
        "scope_of_services",
        "duration",
        "other",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    error: Optional[str] = None


class ClauseRisk(BaseModel):
    risk_level: Literal["none", "low", "medium", "high"]
    risk_type: Literal[
        "none",
        "unlimited_liability",
        "unilateral_termination",
        "no_notice_termination",
        "unfavorable_jurisdiction",
        "ip_transfer_broad",
        "broad_indemnification",
        "payment_ambiguity",
        "one_sided_confidentiality",
        "excessive_penalties",
        "auto_renewal_without_notice",
        "liability_exclusion",
        "other",
    ]
    reason: str = ""
    recommendation: str = ""
    trigger_text: str = ""


class ClauseExplanation(BaseModel):
    summary: str


class ClauseHighlight(BaseModel):
    color: Optional[str] = None
    reason: Optional[str] = None


class ClauseAnalysis(BaseModel):
    clause_id: int
    title: str
    text: str
    classification: ClauseClassification
    risk: ClauseRisk
    explanation: ClauseExplanation
    highlight: ClauseHighlight


class MissingClauseAnalysis(BaseModel):
    present_clauses: List[str]
    missing_clauses: List[str]
    summary: str


class HighRiskClause(BaseModel):
    clause_id: Optional[int] = None
    title: Optional[str] = None
    text: Optional[str] = None
    risk_type: Optional[str] = None
    trigger_text: Optional[str] = None


class ContractReport(BaseModel):
    total_clauses: int
    classification_summary: dict[str, int]
    risk_summary: dict[str, int]
    high_risk_clauses: List[HighRiskClause]


class ContractAnalysisResult(BaseModel):
    status: Literal["success"]
    document_name: str
    total_clauses: int
    clauses: List[ClauseAnalysis]
    missing_clause_analysis: MissingClauseAnalysis
    report: ContractReport