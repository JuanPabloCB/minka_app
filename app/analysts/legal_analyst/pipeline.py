"""
DEPRECATED:
This module belongs to an older legal analysis flow and should not be used
as the main path for the current Legal Analyst architecture.
"""


from typing import Dict, List

from .parser import DocumentParser
from .clause_segmenter import ClauseSegmenter
from .classifier import ClauseClassifier
from .risk_detector import RiskDetector


class LegalAnalysisPipeline:

    def __init__(self):

        self.parser = DocumentParser()
        self.segmenter = ClauseSegmenter()
        self.classifier = ClauseClassifier()
        self.risk_detector = RiskDetector()

    def run(self, file_path: str) -> Dict:

        document_text = self.parser.parse(file_path)
        clauses = self.segmenter.segment(document_text)
        enriched_clauses: List[Dict] = []

        for clause in clauses:

            clause_text = clause["text"]

            # classification
            classification = self.classifier.classify(clause_text)

            # risk detection
            risk = self.risk_detector.detect(clause)

            enriched_clause = {
                **clause,
                "classification": classification,
                "risk": risk
            }

            enriched_clauses.append(enriched_clause)

        return {
            "total_clauses": len(enriched_clauses),
            "clauses": enriched_clauses
        }