from dataclasses import dataclass, field
from typing import List


@dataclass
class LegalAnalystDefinition:
    analyst_id: str
    name: str
    description: str
    supported_goal_types: List[str] = field(default_factory=list)
    accepted_input_types: List[str] = field(default_factory=list)
    available_steps: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)
    default_entry_step: str = "load_contract"
    can_resume: bool = True
    supports_streaming: bool = True


LEGAL_ANALYST_DEFINITION = LegalAnalystDefinition(
    analyst_id="legal_analyst",
    name="Analista Legal",
    description=(
        "Analista especializado en revisión legal de contratos, "
        "detección de hallazgos, priorización de riesgos, "
        "interpretación práctica y generación de contrato marcado."
    ),
    supported_goal_types=[
        "critical_clause_detection",
        "contract_risk_review",
        "marked_contract_export",
        "executive_legal_summary",
    ],
    accepted_input_types=[
        "document_id",
        "pdf",
        "docx",
        "txt",
    ],
    available_steps=[
        "load_contract",
        "detect_findings",
        "prioritize_risks",
        "practical_interpretation",
        "generate_marked_contract",
    ],
    output_types=[
        "findings_table",
        "risk_summary",
        "practical_interpretation",
        "marked_pdf",
        "executive_summary",
    ],
)