from typing import Any, Dict, List

from app.analysts.base_step import BaseStep, BaseStepResult


class PracticalInterpretationStep(BaseStep):
    step_id = "practical_interpretation"
    name = "Interpretación práctica"
    description = (
        "Explica qué significan los hallazgos priorizados en términos prácticos "
        "para el usuario, incluyendo impacto y recomendaciones."
    )

    def execute(self, context: Dict[str, Any]) -> BaseStepResult:
        self.validate()

        shared_state = context.get("shared_state", {}) or {}
        prioritized_result = shared_state.get("prioritize_risks", {}) or {}

        prioritized_risks = prioritized_result.get("prioritized_risks", [])

        if not prioritized_risks:
            return BaseStepResult(
                step_id=self.step_id,
                status="failed",
                output={
                    "interpretations": [],
                    "total_interpretations": 0,
                },
                error=(
                    "No se puede ejecutar 'practical_interpretation' porque no existen "
                    "riesgos priorizados en el contexto."
                ),
            )

        interpretations: List[Dict[str, Any]] = []

        for risk in prioritized_risks:
            severity = risk.get("severity", "low")
            title = risk.get("title", "Hallazgo sin título")

            if severity == "high":
                what_it_means = (
                    f"La cláusula '{title}' podría dejar al cliente en una posición "
                    "contractual desfavorable si ocurre un incumplimiento o conflicto."
                )
                business_impact = (
                    "Podría aumentar exposición legal, reducir capacidad de reclamo "
                    "o limitar compensaciones frente a daños."
                )
                suggested_action = (
                    "Revisar esta redacción con prioridad y evaluar una negociación "
                    "o ajuste antes de firmar."
                )
            elif severity == "medium":
                what_it_means = (
                    f"La cláusula '{title}' puede no ser necesariamente inválida, "
                    "pero sí podría generar fricciones o menor protección contractual."
                )
                business_impact = (
                    "Podría afectar plazos, condiciones de salida, o reducir claridad "
                    "en obligaciones entre las partes."
                )
                suggested_action = (
                    "Validar si la redacción es consistente con el objetivo comercial "
                    "y si conviene precisar mejor el alcance."
                )
            else:
                what_it_means = (
                    f"La cláusula '{title}' no parece crítica, pero podría beneficiarse "
                    "de una redacción más clara o completa."
                )
                business_impact = (
                    "El impacto sería menor, aunque una redacción ambigua puede crear "
                    "dudas interpretativas en el futuro."
                )
                suggested_action = (
                    "Mantener bajo observación y mejorar la precisión jurídica si el caso lo requiere."
                )

            interpretations.append(
                {
                    "finding_id": risk.get("finding_id"),
                    "title": title,
                    "severity": severity,
                    "page": risk.get("page"),
                    "excerpt": risk.get("excerpt"),
                    "what_it_means": what_it_means,
                    "business_impact": business_impact,
                    "suggested_action": suggested_action,
                    "recommendation": risk.get("recommendation"),
                    "attention_level": risk.get("attention_level"),
                }
            )

        general_summary = {
            "headline": "Interpretación práctica completada",
            "summary": (
                "Se generó una interpretación práctica de los riesgos priorizados para "
                "facilitar la toma de decisiones del usuario sobre el contrato."
            ),
            "high_priority_count": len(
                [item for item in interpretations if item["severity"] == "high"]
            ),
            "medium_priority_count": len(
                [item for item in interpretations if item["severity"] == "medium"]
            ),
            "low_priority_count": len(
                [item for item in interpretations if item["severity"] == "low"]
            ),
        }

        return BaseStepResult(
            step_id=self.step_id,
            status="completed",
            output={
                "interpretations": interpretations,
                "total_interpretations": len(interpretations),
                "general_summary": general_summary,
                "message": (
                    "Se generó la interpretación práctica de los riesgos priorizados."
                ),
            },
            error=None,
        )