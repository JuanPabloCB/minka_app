from typing import List, Dict, Any


class ClauseHighlighter:
    """
    Assigns a highlight style to each clause based on risk level
    or, if absent, based on semantic classification.
    """

    TYPE_COLORS = {
        "payment": "blue",
        "termination": "yellow",
        "liability": "orange",
        "confidentiality": "green",
        "intellectual_property": "purple",
        "governing_law": "teal",
        "dispute_resolution": "indigo",
        "force_majeure": "cyan",
        "scope_of_services": "sky",
        "duration": "lime",
    }

    RISK_COLORS = {
        "high": "red",
        "medium": "orange",
        "low": "gray",
        "none": None,
    }

    def highlight(self, clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(clauses, list):
            raise TypeError("clauses must be a list")

        highlighted_clauses = []

        for clause in clauses:
            highlight_color = None
            highlight_reason = None

            risk = clause.get("risk", {})
            risk_level = risk.get("risk_level")

            if risk_level in self.RISK_COLORS and self.RISK_COLORS[risk_level]:
                highlight_color = self.RISK_COLORS[risk_level]
                highlight_reason = f"risk_{risk_level}"

            if highlight_color is None:
                classification = clause.get("classification", {})
                clause_type = classification.get("type")

                if clause_type in self.TYPE_COLORS:
                    highlight_color = self.TYPE_COLORS[clause_type]
                    highlight_reason = f"type_{clause_type}"

            highlighted_clauses.append({
                **clause,
                "highlight": {
                    "color": highlight_color,
                    "reason": highlight_reason
                }
            })

        return highlighted_clauses