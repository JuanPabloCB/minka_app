from typing import Any, Dict, List

from app.analysts.base_step import BaseStep, BaseStepResult


class GenerateMarkedContractStep(BaseStep):
    step_id = "generate_marked_contract"
    name = "Generar contrato marcado"
    description = (
        "Produce una versión exportable del contrato con marcas visuales "
        "sobre cláusulas detectadas o priorizadas."
    )

    def execute(self, context: Dict[str, Any]) -> BaseStepResult:
        self.validate()

        shared_state = context.get("shared_state", {}) or {}
        load_contract_result = shared_state.get("load_contract", {}) or {}
        prioritized_result = shared_state.get("prioritize_risks", {}) or {}
        interpretation_result = shared_state.get("practical_interpretation", {}) or {}

        document_ready = load_contract_result.get("document_ready", False)
        filename = load_contract_result.get("filename")
        prioritized_risks = prioritized_result.get("prioritized_risks", [])
        interpretations = interpretation_result.get("interpretations", [])

        if not document_ready:
            return BaseStepResult(
                step_id=self.step_id,
                status="failed",
                output={
                    "marked_document_ready": False,
                    "marked_sections": [],
                },
                error=(
                    "No se puede generar el contrato marcado porque el documento "
                    "base no está disponible."
                ),
            )

        if not prioritized_risks:
            return BaseStepResult(
                step_id=self.step_id,
                status="failed",
                output={
                    "marked_document_ready": False,
                    "marked_sections": [],
                },
                error=(
                    "No se puede generar el contrato marcado porque no existen "
                    "riesgos priorizados en el contexto."
                ),
            )

        interpretation_map = {
            item.get("finding_id"): item for item in interpretations
        }

        marked_sections: List[Dict[str, Any]] = []

        for risk in prioritized_risks:
            finding_id = risk.get("finding_id")
            interpretation = interpretation_map.get(finding_id, {})

            severity = risk.get("severity", "low")
            if severity == "high":
                highlight_color = "red"
            elif severity == "medium":
                highlight_color = "yellow"
            else:
                highlight_color = "blue"

            marked_sections.append(
                {
                    "finding_id": finding_id,
                    "title": risk.get("title"),
                    "page": risk.get("page"),
                    "excerpt": risk.get("excerpt"),
                    "severity": severity,
                    "highlight_color": highlight_color,
                    "reason": risk.get("reason"),
                    "practical_impact": risk.get("practical_impact"),
                    "recommendation": risk.get("recommendation"),
                    "what_it_means": interpretation.get("what_it_means"),
                    "business_impact": interpretation.get("business_impact"),
                    "suggested_action": interpretation.get("suggested_action"),
                }
            )

        export_filename = None
        if filename:
            if "." in filename:
                name_parts = filename.rsplit(".", 1)
                export_filename = f"{name_parts[0]}_marked.{name_parts[1]}"
            else:
                export_filename = f"{filename}_marked.pdf"
        else:
            export_filename = "contract_marked.pdf"

        export_preview = {
            "artifact_type": "marked_pdf",
            "filename": export_filename,
            "status": "prepared",
            "total_marks": len(marked_sections),
        }

        return BaseStepResult(
            step_id=self.step_id,
            status="completed",
            output={
                "marked_document_ready": True,
                "marked_sections": marked_sections,
                "total_marked_sections": len(marked_sections),
                "export_preview": export_preview,
                "message": (
                    "Se preparó la estructura del contrato marcado para exportación."
                ),
            },
            error=None,
        )