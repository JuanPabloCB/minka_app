from typing import Any, Dict, List

from app.analysts.base_step import BaseStep, BaseStepResult


class PrioritizeRisksStep(BaseStep):
    step_id = "prioritize_risks"
    name = "Priorizar riesgos"
    description = (
        "Ordena los hallazgos detectados según criticidad, nivel de atención "
        "e impacto legal o contractual."
    )

    def execute(self, context: Dict[str, Any]) -> BaseStepResult:
        self.validate()

        shared_state = context.get("shared_state", {}) or {}
        findings_result = shared_state.get("detect_findings", {}) or {}

        findings = findings_result.get("findings", [])

        if not findings:
            return BaseStepResult(
                step_id=self.step_id,
                status="failed",
                output={
                    "prioritized_risks": [],
                    "total_prioritized": 0,
                },
                error=(
                    "No se puede ejecutar 'prioritize_risks' porque no existen "
                    "hallazgos detectados en el contexto."
                ),
            )

        severity_rank = {
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        prioritized_risks: List[Dict[str, Any]] = []

        for finding in findings:
            severity = finding.get("severity", "low")
            rank = severity_rank.get(severity, 0)

            if severity == "high":
                attention_level = "inmediata"
                practical_impact = (
                    "Puede generar una exposición contractual importante para el cliente."
                )
                recommendation = (
                    "Revisar y renegociar esta cláusula antes de aprobar el contrato."
                )
            elif severity == "medium":
                attention_level = "alta"
                practical_impact = (
                    "Puede afectar la ejecución del contrato o reducir margen de protección."
                )
                recommendation = (
                    "Validar si el contexto comercial justifica mantener esta redacción."
                )
            else:
                attention_level = "moderada"
                practical_impact = (
                    "No parece crítico, pero conviene revisarlo para mejorar precisión jurídica."
                )
                recommendation = (
                    "Mantener en observación y ajustar si el caso lo requiere."
                )

            prioritized_risks.append(
                {
                    "finding_id": finding.get("finding_id"),
                    "title": finding.get("title"),
                    "category": finding.get("category"),
                    "severity": severity,
                    "severity_rank": rank,
                    "page": finding.get("page"),
                    "excerpt": finding.get("excerpt"),
                    "reason": finding.get("reason"),
                    "attention_level": attention_level,
                    "practical_impact": practical_impact,
                    "recommendation": recommendation,
                }
            )

        prioritized_risks.sort(
            key=lambda item: item.get("severity_rank", 0),
            reverse=True,
        )

        summary = {
            "high": len([r for r in prioritized_risks if r["severity"] == "high"]),
            "medium": len([r for r in prioritized_risks if r["severity"] == "medium"]),
            "low": len([r for r in prioritized_risks if r["severity"] == "low"]),
        }

        return BaseStepResult(
            step_id=self.step_id,
            status="completed",
            output={
                "prioritized_risks": prioritized_risks,
                "total_prioritized": len(prioritized_risks),
                "summary": summary,
                "message": (
                    "Los hallazgos fueron priorizados según criticidad e impacto práctico."
                ),
            },
            error=None,
        )