from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlannerDecision:
    analyst_id: str
    goal_type: str
    selected_steps: List[str] = field(default_factory=list)
    reasoning: List[str] = field(default_factory=list)


class AnalystPlanner:
    def __init__(self, analyst_id: str):
        self.analyst_id = analyst_id

    def build_plan(
        self,
        goal_type: str,
        inputs: Optional[Dict[str, Any]] = None,
        assigned_macro_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> PlannerDecision:
        """
        Construye una secuencia de steps a ejecutar según la meta
        y el contexto disponible.
        """
        inputs = inputs or {}
        assigned_macro_steps = assigned_macro_steps or []

        has_document = bool(inputs.get("document_id") or inputs.get("uploaded_file"))
        desired_output = str(inputs.get("desired_output", "")).lower()

        macro_text = self._build_macro_text(assigned_macro_steps)

        selected_steps: List[str] = []
        reasoning: List[str] = []

        # 1. Entrada del documento
        selected_steps.append("load_contract")
        if has_document:
            reasoning.append(
                "Se incluye 'load_contract' para validar o reutilizar el documento ya disponible."
            )
        else:
            reasoning.append(
                "Se incluye 'load_contract' porque el analista necesita recibir o preparar el documento."
            )

        # 2. Detección base
        selected_steps.append("detect_findings")
        reasoning.append(
            "Se incluye 'detect_findings' porque es la base del análisis legal inicial."
        )

        # 3. Priorización
        selected_steps.append("prioritize_risks")
        reasoning.append(
            "Se incluye 'prioritize_risks' para ordenar hallazgos por criticidad e impacto."
        )

        # 4. Interpretación práctica: la metemos si la meta o los macro pasos sugieren explicación
        should_include_practical = self._should_include_practical_interpretation(
            goal_type=goal_type,
            desired_output=desired_output,
            macro_text=macro_text,
        )

        if should_include_practical:
            selected_steps.append("practical_interpretation")
            reasoning.append(
                "Se incluye 'practical_interpretation' porque la meta requiere explicación práctica o interpretación de los hallazgos."
            )
        else:
            reasoning.append(
                "Se omite 'practical_interpretation' porque los macro pasos no exigen una explicación práctica detallada en esta fase."
            )

        # 5. Contrato marcado: solo si la meta o macro pasos apuntan a exportación marcada
        should_include_marked_contract = self._should_include_marked_contract(
            goal_type=goal_type,
            desired_output=desired_output,
            macro_text=macro_text,
        )

        if should_include_marked_contract:
            selected_steps.append("generate_marked_contract")
            reasoning.append(
                "Se incluye 'generate_marked_contract' porque la meta o los macro pasos requieren una salida exportable marcada."
            )
        else:
            reasoning.append(
                "Se omite 'generate_marked_contract' porque la salida esperada parece ser estructurada o explicativa, no un contrato marcado."
            )

        if assigned_macro_steps:
            reasoning.append(
                f"Se recibieron {len(assigned_macro_steps)} macro pasos asignados por el orquestador y se usaron como criterio de selección."
            )

        return PlannerDecision(
            analyst_id=self.analyst_id,
            goal_type=goal_type,
            selected_steps=selected_steps,
            reasoning=reasoning,
        )

    def _build_macro_text(self, assigned_macro_steps: List[Dict[str, Any]]) -> str:
        """
        Une title/description/expected_output de los macro pasos
        en un solo texto para facilitar reglas simples.
        """
        parts: List[str] = []

        for step in assigned_macro_steps:
            title = str(step.get("title", "")).strip()
            description = str(step.get("description", "")).strip()
            expected_output = str(step.get("expected_output", "")).strip()

            if title:
                parts.append(title.lower())
            if description:
                parts.append(description.lower())
            if expected_output:
                parts.append(expected_output.lower())

        return " | ".join(parts)

    def _should_include_practical_interpretation(
        self,
        goal_type: str,
        desired_output: str,
        macro_text: str,
    ) -> bool:
        practical_keywords = [
            "explicar",
            "interpret",
            "interpretación",
            "impacto práctico",
            "implicancias",
            "recomendación",
            "recomendaciones",
            "riesgo",
            "riesgos",
            "explicación",
        ]

        if goal_type in {
            "critical_clause_detection",
            "contract_risk_review",
            "executive_legal_summary",
        }:
            return True

        if desired_output in {
            "practical_interpretation",
            "structured_legal_findings",
            "executive_summary",
        }:
            return True

        return any(keyword in macro_text for keyword in practical_keywords)

    def _should_include_marked_contract(
        self,
        goal_type: str,
        desired_output: str,
        macro_text: str,
    ) -> bool:
        marked_keywords = [
            "contrato marcado",
            "marcado",
            "highlight",
            "resaltar",
            "resaltado",
            "exportar contrato",
            "pdf marcado",
            "cláusulas marcadas",
            "con marcas",
        ]

        if goal_type in {
            "marked_contract_export",
        }:
            return True

        if desired_output in {
            "marked_pdf",
            "marked_contract",
        }:
            return True

        return any(keyword in macro_text for keyword in marked_keywords)