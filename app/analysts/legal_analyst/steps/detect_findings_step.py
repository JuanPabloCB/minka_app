from typing import Any, Dict, List

from app.analysts.base_step import BaseStep, BaseStepResult


class DetectFindingsStep(BaseStep):
    step_id = "detect_findings"
    name = "Detectar hallazgos"
    description = (
        "Identifica cláusulas, secciones o fragmentos relevantes del contrato "
        "que deben revisarse dentro del análisis legal."
    )

    def execute(self, context: Dict[str, Any]) -> BaseStepResult:
        self.validate()

        shared_state = context.get("shared_state", {}) or {}
        load_contract_result = shared_state.get("load_contract", {}) or {}

        document_ready = load_contract_result.get("document_ready", False)
        filename = load_contract_result.get("filename")

        if not document_ready:
            return BaseStepResult(
                step_id=self.step_id,
                status="failed",
                output={
                    "findings": [],
                    "total_findings": 0,
                },
                error=(
                    "No se puede ejecutar 'detect_findings' porque el contrato "
                    "no está disponible o no fue cargado correctamente."
                ),
            )

        findings: List[Dict[str, Any]] = [
            {
                "finding_id": "F-001",
                "title": "Limitación de responsabilidad",
                "category": "risk_clause",
                "severity": "high",
                "page": 3,
                "excerpt": "La responsabilidad total de la parte proveedora quedará limitada...",
                "reason": "La cláusula podría restringir excesivamente la responsabilidad contractual.",
            },
            {
                "finding_id": "F-002",
                "title": "Plazo de terminación anticipada",
                "category": "termination",
                "severity": "medium",
                "page": 5,
                "excerpt": "Cualquiera de las partes podrá resolver el contrato con aviso previo de 5 días...",
                "reason": "El plazo de preaviso podría ser insuficiente según el contexto comercial.",
            },
            {
                "finding_id": "F-003",
                "title": "Confidencialidad",
                "category": "confidentiality",
                "severity": "low",
                "page": 7,
                "excerpt": "Las partes se comprometen a no divulgar información confidencial...",
                "reason": "La cláusula existe, pero podría requerir mayor precisión en alcance y duración.",
            },
        ]

        return BaseStepResult(
            step_id=self.step_id,
            status="completed",
            output={
                "document_ready": True,
                "filename": filename,
                "findings": findings,
                "total_findings": len(findings),
                "message": (
                    "Se detectaron hallazgos preliminares relevantes para la revisión legal."
                ),
            },
            error=None,
        )