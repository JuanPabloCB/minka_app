from typing import Dict, Any, Optional


class ClauseExplainer:
    """
    Generates human-readable explanations for legal clauses.
    Rule-based and stable for MVP.
    """

    def explain(self, clause_text: str, clause_type: Optional[str] = None) -> Dict[str, Any]:
        if not isinstance(clause_text, str):
            raise TypeError("clause_text must be a string")

        text = clause_text.lower().strip()

        if not text:
            return {"summary": "No explanation available for an empty clause."}

        if clause_type == "termination":
            return {
                "summary": (
                    "This clause explains how the contract may be ended, including the conditions, "
                    "timing, and rights of the parties to terminate the agreement."
                )
            }

        if clause_type == "payment":
            return {
                "summary": (
                    "This clause describes the financial obligations between the parties, "
                    "including payment timing, invoicing, compensation, or related monetary terms."
                )
            }

        if clause_type == "liability":
            return {
                "summary": (
                    "This clause defines legal responsibility for damages, losses, or contractual breaches, "
                    "including how liability may be assigned or limited."
                )
            }

        if clause_type == "confidentiality":
            return {
                "summary": (
                    "This clause requires certain information to remain confidential and limits disclosure "
                    "to third parties unless permitted by the agreement."
                )
            }

        if clause_type == "governing_law":
            return {
                "summary": (
                    "This clause identifies which jurisdiction's laws will govern the interpretation "
                    "and enforcement of the agreement."
                )
            }

        if clause_type == "dispute_resolution":
            return {
                "summary": (
                    "This clause explains how disputes between the parties should be resolved, "
                    "for example through arbitration, mediation, or court proceedings."
                )
            }

        if clause_type == "intellectual_property":
            return {
                "summary": (
                    "This clause defines ownership or use rights over intellectual property, "
                    "such as software, content, inventions, or related deliverables."
                )
            }

        if clause_type == "force_majeure":
            return {
                "summary": (
                    "This clause addresses extraordinary events beyond the parties' control "
                    "that may prevent or delay performance under the agreement."
                )
            }

        if clause_type == "scope_of_services":
            return {
                "summary": (
                    "This clause describes the services, work, or deliverables that one party "
                    "must provide under the agreement."
                )
            }

        if clause_type == "duration":
            return {
                "summary": (
                    "This clause defines the duration of the agreement, including when it starts, "
                    "how long it lasts, and whether it can be renewed or ended earlier."
                )
            }

        if "terminate" in text:
            return {
                "summary": (
                    "This clause explains how the contract may be ended, including the conditions, "
                    "timing, and rights of the parties to terminate the agreement."
                )
            }

        if "pay" in text or "payment" in text or "invoice" in text:
            return {
                "summary": (
                    "This clause describes the financial obligations between the parties, "
                    "including payment timing, invoicing, compensation, or related monetary terms."
                )
            }

        if "liable" in text or "liability" in text:
            return {
                "summary": (
                    "This clause defines legal responsibility for damages, losses, or contractual breaches, "
                    "including how liability may be assigned or limited."
                )
            }

        if "confidential" in text:
            return {
                "summary": (
                    "This clause requires certain information to remain confidential and limits disclosure "
                    "to third parties unless permitted by the agreement."
                )
            }

        return {
            "summary": "This clause defines part of the agreement between the parties."
        }