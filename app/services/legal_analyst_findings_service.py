from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models.analyst_run import AnalystRun
from app.db.models.plan_step import PlanStep
from app.services.legal_findings_v2 import LegalAnalystFindingsPipelineV2
from app.services.legal_findings_v2.pdf_layout_extractor import PdfLayoutExtractor
from app.services.legal_findings_v2.text_cleaner import LegalTextCleaner
from app.services.legal_findings_v2.selective_restorer import SelectiveTextRestorer

MODEL = "gpt-4.1-mini"


class LegalAnalystFindingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pipeline_v2 = LegalAnalystFindingsPipelineV2(model=MODEL)
        self.layout_extractor = PdfLayoutExtractor()
        self.text_cleaner = LegalTextCleaner()
        self.text_restorer = SelectiveTextRestorer(model=MODEL)

    def _print_token_usage(self, label: str, usage: dict[str, int]) -> None:
        print(f"===== TOKEN USAGE: {label} =====")
        print("input_tokens:", usage.get("input_tokens", 0))
        print("output_tokens:", usage.get("output_tokens", 0))
        print("total_tokens:", usage.get("total_tokens", 0))
        print("================================")

    def _build_findings_summary(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        by_level: dict[str, int] = {}
        by_category: dict[str, int] = {}
        by_review_status: dict[str, int] = {}

        for finding in findings:
            level = str(finding.get("level") or "unknown")
            category = str(finding.get("category") or "unknown")
            review_status = str(finding.get("review_status") or "unknown")

            by_level[level] = by_level.get(level, 0) + 1
            by_category[category] = by_category.get(category, 0) + 1
            by_review_status[review_status] = by_review_status.get(review_status, 0) + 1

        return {
            "total_findings": len(findings),
            "by_level": by_level,
            "by_category": by_category,
            "by_review_status": by_review_status,
        }

    def _resolve_pdf_path(self, run: AnalystRun, run_context: dict[str, Any]) -> str | None:
        """
        Busca una ruta PDF probable en run.result o run_context.
        Ajusta aquí si en tu sistema usas otra key.
        """
        result = dict(run.result or {})
        candidates = [
            result.get("pdf_path"),
            result.get("document_path"),
            result.get("source_file_path"),
            result.get("uploaded_file_path"),
            result.get("file_path"),
            run_context.get("pdf_path"),
            run_context.get("document_path"),
            run_context.get("source_file_path"),
            run_context.get("uploaded_file_path"),
            run_context.get("file_path"),
        ]

        for value in candidates:
            if isinstance(value, str) and value.strip().lower().endswith(".pdf"):
                return value.strip()

        return None

    def _build_empty_error_payload(
        self,
        *,
        run: AnalystRun,
        run_context: dict[str, Any],
        macro_step_id: str | None,
        detection_mode: str,
        clause_targets: list[str],
        finding_targets: list[str],
        token_usage_totals: dict[str, int],
        formal_findings: list[dict[str, Any]],
        functional_findings: list[dict[str, Any]],
        error_code: str,
        error_detail: str,
        coverage_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = dict(run.result or {})
        result["findings"] = []
        result["formal_findings"] = formal_findings
        result["functional_findings"] = functional_findings
        result["atomic_findings"] = []
        result["list_item_findings"] = []
        result["bad_fragment_findings"] = []
        result["confirmed_main_clauses"] = []
        result["possible_main_clauses"] = []
        result["missing_expected_ranks"] = []
        result["needs_review"] = []
        result["total_findings"] = 0
        result["finding_targets"] = finding_targets
        result["detection_mode"] = detection_mode
        result["clause_targets"] = clause_targets
        result["findings_summary"] = {}
        result["coverage_summary"] = coverage_summary or {
            "confirmed_main_clause_count": 0,
            "possible_main_clause_count": 0,
            "formal_clause_count": 0,
            "functional_finding_count": len(functional_findings),
            "low_coverage_clause_count": 0,
            "second_pass_executed": True,
            "second_pass_added_findings": 0,
            "per_clause": [],
        }
        result["unit_summary"] = {
            "confirmed_main_clause_count": 0,
            "possible_main_clause_count": 0,
            "formal_clause_count": 0,
            "subclause_count": 0,
            "list_item_count": 0,
            "atomic_provision_count": 0,
            "total_contract_units": 0,
            "appendix_detected": False,
            "appendix_length": 0,
        }
        result["current_micro_step"] = "detect_findings"
        result["llm_usage"] = {
            "model": MODEL,
            "input_tokens": token_usage_totals.get("input_tokens", 0),
            "output_tokens": token_usage_totals.get("output_tokens", 0),
            "total_tokens": token_usage_totals.get("total_tokens", 0),
        }
        result["error_code"] = error_code
        result["error_detail"] = error_detail

        run.result = result
        run.status = "error"
        run.audit_log = (run.audit_log or "") + f" | Error en detect_findings: {error_code}: {error_detail}"

        self.db.commit()
        self.db.refresh(run)

        return {
            "ok": False,
            "run_id": str(run.id),
            "macro_step_id": macro_step_id or run_context.get("current_macro_step_id"),
            "macro_step_title": run_context.get("current_macro_step_title"),
            "micro_step": "detect_findings",
            "detection_mode": detection_mode,
            "clause_targets": clause_targets,
            "finding_targets": finding_targets,
            "total_findings": 0,
            "findings": [],
            "formal_findings": formal_findings,
            "functional_findings": functional_findings,
            "atomic_findings": [],
            "list_item_findings": [],
            "bad_fragment_findings": [],
            "confirmed_main_clauses": [],
            "possible_main_clauses": [],
            "missing_expected_ranks": [],
            "needs_review": [],
            "summary": {},
            "message": f"No se pudo completar la detección: {error_detail}",
        }

    