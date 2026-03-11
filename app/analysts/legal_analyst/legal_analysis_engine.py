from pathlib import Path
from typing import Dict, Any, List

from app.analysts.legal_analyst.parser import DocumentParser
from app.analysts.legal_analyst.clause_segmenter import ClauseSegmenter
from app.analysts.legal_analyst.semantic_clause_classifier import SemanticClauseClassifier
from app.analysts.legal_analyst.risk_clause_detector import RiskClauseDetector
from app.analysts.legal_analyst.missing_clause_detector import MissingClauseDetector
from app.analysts.legal_analyst.clause_explainer import ClauseExplainer
from app.analysts.legal_analyst.clause_highlighter import ClauseHighlighter
from app.analysts.legal_analyst.contract_analysis_report import ContractAnalysisReport
from app.analysts.legal_analyst.schemas import (
    ClauseAnalysis,
    ContractAnalysisResult,
)


class LegalAnalysisEngine:
    """
    Main orchestration engine for legal contract analysis.

    Pipeline:
    Document -> Clause Segmentation -> Classification -> Risk Detection
             -> Explanation -> Missing Clause Detection -> Highlighting -> Report
    """

    def __init__(self):
        self.parser = DocumentParser()
        self.segmenter = ClauseSegmenter()
        self.classifier = SemanticClauseClassifier()
        self.risk_detector = RiskClauseDetector()
        self.missing_clause_detector = MissingClauseDetector()
        self.explainer = ClauseExplainer()
        self.highlighter = ClauseHighlighter()
        self.report_generator = ContractAnalysisReport()

    def analyze_contract(self, file_path: str) -> Dict[str, Any]:
        if not isinstance(file_path, str):
            raise TypeError("file_path must be a string")

        document_path = Path(file_path)
        document_name = document_path.name

        document_text = self.parser.parse(file_path)
        clauses = self.segmenter.segment(document_text)

        analyzed_clauses: List[Dict[str, Any]] = []

        for clause in clauses:
            analyzed_clause = self._analyze_single_clause(clause)
            analyzed_clauses.append(analyzed_clause)

        highlighted_clauses = self.highlighter.highlight(analyzed_clauses)
        missing_clause_analysis = self.missing_clause_detector.detect(highlighted_clauses)
        report = self.report_generator.generate(highlighted_clauses)

        validated_clauses = [
            ClauseAnalysis.model_validate(clause)
            for clause in highlighted_clauses
        ]

        result = ContractAnalysisResult(
            status="success",
            document_name=document_name,
            total_clauses=len(validated_clauses),
            clauses=validated_clauses,
            missing_clause_analysis=missing_clause_analysis,
            report=report,
        )

        return result.model_dump()

    def _analyze_single_clause(self, clause: Dict[str, Any]) -> Dict[str, Any]:
        clause_id = clause.get("clause_id")
        title = clause.get("title")
        clause_text = clause.get("text", "")

        classification = self.classifier.classify(clause_text)
        clause_type = classification.get("type")

        risk = self.risk_detector.detect(clause_text, clause_type)
        explanation = self.explainer.explain(clause_text, clause_type)

        return {
            "clause_id": clause_id,
            "title": title,
            "text": clause_text,
            "classification": classification,
            "risk": risk,
            "explanation": explanation,
        }