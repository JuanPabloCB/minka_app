from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.analysts.legal_analyst.parser import DocumentParser
from app.analysts.legal_analyst.clause_segmenter import ClauseSegmenter
from app.analysts.legal_analyst.semantic_clause_classifier import SemanticClauseClassifier
from app.analysts.legal_analyst.risk_clause_detector import RiskClauseDetector
from app.analysts.legal_analyst.missing_clause_detector import MissingClauseDetector
from app.analysts.legal_analyst.clause_explainer import ClauseExplainer
from app.analysts.legal_analyst.clause_highlighter import ClauseHighlighter
from app.analysts.legal_analyst.contract_analysis_report import ContractAnalysisReport
from app.analysts.legal_analyst.schemas import ClauseAnalysis


class LegalExecutionError(Exception):
    """Base execution error for the Legal Analyst."""


class LegalExecutor:
    """
    Executes a dynamic legal analysis plan using the canonical Legal Analyst modules.

    Design goals:
    - deterministic orchestration
    - explicit state transitions
    - safe dependency checks
    - partial-context execution
    - clean separation from old/legacy pipeline code
    """

    VALID_STEPS = {
        "parse",
        "segment",
        "classify",
        "detect_risk",
        "detect_missing",
        "explain",
        "highlight",
        "report",
    }

    def __init__(self):
        self.parser = DocumentParser()
        self.segmenter = ClauseSegmenter()
        self.classifier = SemanticClauseClassifier()
        self.risk_detector = RiskClauseDetector()
        self.missing_clause_detector = MissingClauseDetector()
        self.explainer = ClauseExplainer()
        self.highlighter = ClauseHighlighter()
        self.report_generator = ContractAnalysisReport()

    def execute(self, plan: List[str], file_path: str) -> Dict[str, Any]:
        """
        Execute a validated legal analysis plan against a document.

        Returns a context dictionary that contains:
        - plan
        - document metadata
        - intermediate artifacts
        - final artifacts depending on the requested steps
        """
        self._validate_inputs(plan, file_path)

        context: Dict[str, Any] = {
            "status": "success",
            "file_path": file_path,
            "document_name": Path(file_path).name,
            "plan": plan,
        }

        for step in plan:
            self._execute_step(step, context)

        return context

    def _execute_step(self, step: str, context: Dict[str, Any]) -> None:
        if step == "parse":
            self._step_parse(context)
            return

        if step == "segment":
            self._step_segment(context)
            return

        if step == "classify":
            self._step_classify(context)
            return

        if step == "detect_risk":
            self._step_detect_risk(context)
            return

        if step == "detect_missing":
            self._step_detect_missing(context)
            return

        if step == "explain":
            self._step_explain(context)
            return

        if step == "highlight":
            self._step_highlight(context)
            return

        if step == "report":
            self._step_report(context)
            return

        raise LegalExecutionError(f"Unsupported execution step: {step}")

    def _step_parse(self, context: Dict[str, Any]) -> None:
        file_path = context["file_path"]
        document_text = self.parser.parse(file_path)
        context["document_text"] = document_text

    def _step_segment(self, context: Dict[str, Any]) -> None:
        document_text = self._require_context_key(context, "document_text")
        clauses = self.segmenter.segment(document_text)
        context["clauses"] = clauses

    def _step_classify(self, context: Dict[str, Any]) -> None:
        clauses = self._require_context_key(context, "clauses")

        classified_clauses: List[Dict[str, Any]] = []

        for clause in clauses:
            clause_text = clause.get("text", "")
            classification = self.classifier.classify(clause_text)

            classified_clause = {
                **clause,
                "classification": classification,
            }
            classified_clauses.append(classified_clause)

        context["clauses"] = classified_clauses

    def _step_detect_risk(self, context: Dict[str, Any]) -> None:
        clauses = self._require_context_key(context, "clauses")

        risk_enriched_clauses: List[Dict[str, Any]] = []

        for clause in clauses:
            classification = clause.get("classification")
            if not isinstance(classification, dict):
                raise LegalExecutionError("detect_risk requires classified clauses")

            clause_text = clause.get("text", "")
            clause_type = classification.get("type")
            risk = self.risk_detector.detect(clause_text, clause_type)

            enriched_clause = {
                **clause,
                "risk": risk,
            }
            risk_enriched_clauses.append(enriched_clause)

        context["clauses"] = risk_enriched_clauses

    def _step_detect_missing(self, context: Dict[str, Any]) -> None:
        clauses = self._require_context_key(context, "clauses")

        self._ensure_classification_present(clauses)

        missing_clause_analysis = self.missing_clause_detector.detect(clauses)
        context["missing_clause_analysis"] = missing_clause_analysis

    def _step_explain(self, context: Dict[str, Any]) -> None:
        clauses = self._require_context_key(context, "clauses")

        self._ensure_classification_present(clauses)

        explained_clauses: List[Dict[str, Any]] = []

        for clause in clauses:
            clause_text = clause.get("text", "")
            clause_type = clause["classification"].get("type")
            explanation = self.explainer.explain(clause_text, clause_type)

            explained_clause = {
                **clause,
                "explanation": explanation,
            }
            explained_clauses.append(explained_clause)

        context["clauses"] = explained_clauses

    def _step_highlight(self, context: Dict[str, Any]) -> None:
        clauses = self._require_context_key(context, "clauses")

        # highlight can work with classification only, but becomes richer if risk already exists
        self._ensure_classification_present(clauses)

        highlighted_clauses = self.highlighter.highlight(clauses)
        context["clauses"] = highlighted_clauses

    def _step_report(self, context: Dict[str, Any]) -> None:
        clauses = self._require_context_key(context, "clauses")
        report = self.report_generator.generate(clauses)
        context["report"] = report

    def _validate_inputs(self, plan: List[str], file_path: str) -> None:
        if not isinstance(plan, list):
            raise TypeError("plan must be a list")

        if not plan:
            raise ValueError("plan cannot be empty")

        if not isinstance(file_path, str):
            raise TypeError("file_path must be a string")

        if not file_path.strip():
            raise ValueError("file_path cannot be empty")

        invalid_steps = [step for step in plan if step not in self.VALID_STEPS]
        if invalid_steps:
            raise ValueError(f"Invalid execution steps: {invalid_steps}")

    def _require_context_key(self, context: Dict[str, Any], key: str) -> Any:
        if key not in context:
            raise LegalExecutionError(f"Required context key missing: {key}")
        return context[key]

    def _ensure_classification_present(self, clauses: List[Dict[str, Any]]) -> None:
        for clause in clauses:
            if "classification" not in clause:
                raise LegalExecutionError("This step requires classified clauses")

    def validate_clause_artifacts(self, clauses: List[Dict[str, Any]]) -> List[ClauseAnalysis]:
        """
        Optional helper:
        validates clause artifacts using the canonical ClauseAnalysis schema.

        Useful when the caller expects fully enriched clause outputs.
        """
        validated = []
        for clause in clauses:
            validated.append(ClauseAnalysis.model_validate(clause))
        return validated