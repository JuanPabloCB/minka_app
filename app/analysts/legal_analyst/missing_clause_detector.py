from typing import List, Dict, Any, Set


class MissingClauseDetector:
    """
    Detects potentially missing critical clauses based on
    the set of clause types identified in the contract.

    Deterministic by design for stability and lower cost.
    """

    DEFAULT_REQUIRED_CLAUSES = {
        "scope_of_services",
        "payment",
        "duration",
        "termination",
        "liability",
        "confidentiality",
        "governing_law",
        "dispute_resolution",
        "force_majeure",
    }

    def __init__(self, required_clauses: Set[str] | None = None):
        self.required_clauses = required_clauses or self.DEFAULT_REQUIRED_CLAUSES

    def detect(self, clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(clauses, list):
            raise TypeError("clauses must be a list")

        present_clauses = self._extract_present_clause_types(clauses)
        missing_clauses = sorted(self.required_clauses - present_clauses)

        return {
            "present_clauses": sorted(present_clauses),
            "missing_clauses": missing_clauses,
            "summary": self._build_summary(missing_clauses)
        }

    def _extract_present_clause_types(self, clauses: List[Dict[str, Any]]) -> Set[str]:
        detected: Set[str] = set()

        for clause in clauses:
            classification = clause.get("classification", {})
            clause_type = classification.get("type")

            if isinstance(clause_type, str) and clause_type.strip() and clause_type != "other":
                detected.add(clause_type)

        return detected

    def _build_summary(self, missing_clauses: List[str]) -> str:
        if not missing_clauses:
            return "No critical missing clauses were detected based on the current clause taxonomy."

        joined = ", ".join(missing_clauses)
        return f"The contract may be missing the following critical clauses: {joined}."