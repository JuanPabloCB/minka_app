from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StepChatScope:
    mode: str = "step_only"
    allowed_topics: List[str] = field(default_factory=list)


@dataclass
class StepInitialMessage:
    id: str
    type: str
    content: str
    animate: bool = True


@dataclass
class StepRenderBlock:
    id: str
    type: str
    label: Optional[str] = None
    accepted_formats: List[str] = field(default_factory=list)


@dataclass
class LegalStepDefinition:
    step_id: str
    name: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    optional: bool = False
    output_type: Optional[str] = None
    chat_scope: StepChatScope = field(default_factory=StepChatScope)
    initial_messages: List[StepInitialMessage] = field(default_factory=list)
    render_blocks: List[StepRenderBlock] = field(default_factory=list)


LEGAL_STEP_CATALOG = {
    "load_contract": LegalStepDefinition(
        step_id="load_contract",
        name="Cargar contrato",
        description=(
            "Recibe el contrato desde el orquestador o desde carga directa del usuario, "
            "y valida que exista un documento disponible para el análisis."
        ),
        depends_on=[],
        requires_confirmation=False,
        optional=False,
        output_type="document_context",
        chat_scope=StepChatScope(
            mode="step_only",
            allowed_topics=[
                "subida de archivo",
                "formatos permitidos",
                "validación del contrato",
                "uso de este paso",
            ],
        ),
        initial_messages=[
            StepInitialMessage(
                id="msg_load_contract_intro_1",
                type="assistant_text",
                content="Perfecto. Para comenzar el análisis legal, sube el contrato en PDF, DOCX o TXT.",
                animate=True,
            )
        ],
        render_blocks=[
            StepRenderBlock(
                id="block_load_contract_uploader_1",
                type="file_uploader",
                label="Arrastra y suelta el archivo aquí, o súbelo desde tu equipo.",
                accepted_formats=["pdf", "docx", "txt"],
            )
        ],
    ),
    "detect_findings": LegalStepDefinition(
        step_id="detect_findings",
        name="Detectar hallazgos",
        description=(
            "Identifica cláusulas, secciones o fragmentos relevantes del contrato "
            "que deben revisarse dentro del análisis legal."
        ),
        depends_on=["load_contract"],
        requires_confirmation=True,
        optional=False,
        output_type="findings_table",
        chat_scope=StepChatScope(
            mode="step_only",
            allowed_topics=[
                "hallazgos detectados",
                "cláusulas encontradas",
                "fragmentos relevantes",
                "alcance de este paso",
            ],
        ),
        initial_messages=[
            StepInitialMessage(
                id="msg_detect_findings_intro_1",
                type="assistant_text",
                content="Ya recibí el contrato. En este paso identificaré cláusulas y fragmentos relevantes para la revisión legal inicial.",
                animate=True,
            )
        ],
        render_blocks=[],
    ),
    "prioritize_risks": LegalStepDefinition(
        step_id="prioritize_risks",
        name="Priorizar riesgos",
        description=(
            "Ordena los hallazgos detectados según criticidad, nivel de atención "
            "e impacto legal o contractual."
        ),
        depends_on=["detect_findings"],
        requires_confirmation=True,
        optional=False,
        output_type="risk_summary",
        chat_scope=StepChatScope(
            mode="step_only",
            allowed_topics=[
                "priorización de riesgos",
                "criticidad",
                "nivel de atención",
                "impacto contractual",
            ],
        ),
        initial_messages=[
            StepInitialMessage(
                id="msg_prioritize_risks_intro_1",
                type="assistant_text",
                content="Ahora priorizaré los hallazgos según criticidad e impacto para destacar qué requiere atención primero.",
                animate=True,
            )
        ],
        render_blocks=[],
    ),
    "practical_interpretation": LegalStepDefinition(
        step_id="practical_interpretation",
        name="Interpretación práctica",
        description=(
            "Explica qué significan los hallazgos priorizados en términos prácticos "
            "para el usuario, incluyendo impacto y recomendaciones."
        ),
        depends_on=["prioritize_risks"],
        requires_confirmation=True,
        optional=False,
        output_type="practical_interpretation",
        chat_scope=StepChatScope(
            mode="step_only",
            allowed_topics=[
                "interpretación práctica",
                "impacto práctico",
                "recomendaciones",
                "qué significa este riesgo",
            ],
        ),
        initial_messages=[
            StepInitialMessage(
                id="msg_practical_interpretation_intro_1",
                type="assistant_text",
                content="En este paso traduciré los hallazgos priorizados a implicancias prácticas y recomendaciones accionables.",
                animate=True,
            )
        ],
        render_blocks=[],
    ),
    "generate_marked_contract": LegalStepDefinition(
        step_id="generate_marked_contract",
        name="Generar contrato marcado",
        description=(
            "Produce una versión exportable del contrato con marcas visuales "
            "sobre cláusulas detectadas o priorizadas."
        ),
        depends_on=["prioritize_risks"],
        requires_confirmation=True,
        optional=True,
        output_type="marked_pdf",
        chat_scope=StepChatScope(
            mode="step_only",
            allowed_topics=[
                "contrato marcado",
                "exportación",
                "marcas visuales",
                "salida final",
            ],
        ),
        initial_messages=[
            StepInitialMessage(
                id="msg_generate_marked_contract_intro_1",
                type="assistant_text",
                content="Finalmente, prepararé una versión exportable del contrato con marcas sobre los puntos relevantes detectados.",
                animate=True,
            )
        ],
        render_blocks=[],
    ),
}


def get_step_definition(step_id: str) -> LegalStepDefinition:
    if step_id not in LEGAL_STEP_CATALOG:
        raise ValueError(f"Step '{step_id}' no existe en el catálogo del Analista Legal.")
    return LEGAL_STEP_CATALOG[step_id]


def list_step_definitions() -> List[LegalStepDefinition]:
    return list(LEGAL_STEP_CATALOG.values())