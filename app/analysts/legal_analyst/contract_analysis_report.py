from typing import List, Dict, Any


class ContractAnalysisReport:
    """
    Generates an aggregated report from analyzed clauses.
    """

    def generate(self, clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(clauses, list):
            raise TypeError("clauses must be a list")

        total_clauses = len(clauses)
        classification_counts: Dict[str, int] = {}
        risk_counts = {
            "high": 0,
            "medium": 0,
            "low": 0,
            "none": 0
        }
        high_risk_clauses = []

        for clause in clauses:
            classification = clause.get("classification", {})
            clause_type = classification.get("type")

            if clause_type:
                classification_counts[clause_type] = classification_counts.get(clause_type, 0) + 1

            risk = clause.get("risk", {})
            risk_level = risk.get("risk_level", "none")

            if risk_level in risk_counts:
                risk_counts[risk_level] += 1

            if risk_level == "high":
                high_risk_clauses.append({
                    "clause_id": clause.get("clause_id"),
                    "title": clause.get("title"),
                    "text": clause.get("text"),
                    "risk_type": risk.get("risk_type"),
                    "trigger_text": risk.get("trigger_text")
                })

        return {
            "total_clauses": total_clauses,
            "classification_summary": classification_counts,
            "risk_summary": risk_counts,
            "high_risk_clauses": high_risk_clauses
        }