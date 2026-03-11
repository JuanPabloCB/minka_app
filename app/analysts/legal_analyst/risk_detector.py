"""
DEPRECATED:
This module belongs to an older legal analysis flow and should not be used
as the main path for the current Legal Analyst architecture.
"""




class RiskDetector:

    def detect(self, clause):

        text = clause["text"].lower()

        risk_level = "low"
        risk_type = None

        if "unlimited liability" in text:
            risk_level = "high"
            risk_type = "unlimited_liability"

        elif "terminate at any time" in text:
            risk_level = "medium"
            risk_type = "one_sided_termination"

        elif "without notice" in text:
            risk_level = "medium"
            risk_type = "termination_without_notice"

        elif "not liable for any damages" in text:
            risk_level = "high"
            risk_type = "liability_exclusion"

        return {
            "risk_level": risk_level,
            "risk_type": risk_type
        }