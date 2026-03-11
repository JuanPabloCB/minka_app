from typing import Dict, Any, Optional
import json
import re

from app.core.ai_gateway import AIGateway
from app.analysts.legal_analyst.prompt_framework import PromptFramework


class RiskClauseDetector:
    """
    Detects legal risks in a single clause.

    Balanced strategy:
    1. Deterministic rules for explicit risks.
    2. AI only for critical clause types or suspicious clauses.
    3. Stable fallback if AI response is invalid.
    """

    VALID_RISK_LEVELS = {"none", "low", "medium", "high"}

    VALID_RISK_TYPES = [
        "none",
        "unlimited_liability",
        "unilateral_termination",
        "no_notice_termination",
        "unfavorable_jurisdiction",
        "ip_transfer_broad",
        "broad_indemnification",
        "payment_ambiguity",
        "one_sided_confidentiality",
        "excessive_penalties",
        "auto_renewal_without_notice",
        "liability_exclusion",
        "other",
    ]

    CRITICAL_CLAUSE_TYPES = {
        "liability",
        "termination",
        "intellectual_property",
        "governing_law",
        "dispute_resolution",
        "payment",
        "confidentiality",
    }

    SUSPICIOUS_KEYWORDS = [
        "penalty",
        "interest",
        "exclusive",
        "without notice",
        "without limitation",
        "liable",
        "liability",
        "indemnify",
        "arbitration",
        "governed by",
        "laws of",
        "terminate",
        "confidential",
        "renew",
        "automatically renew",
        "damages",
    ]

    def __init__(self):
        self.ai = AIGateway()

    def detect(self, clause_text: str, clause_type: Optional[str] = None) -> Dict[str, Any]:
        if not isinstance(clause_text, str):
            raise TypeError("clause_text must be a string")

        clause_text = clause_text.strip()
        if not clause_text:
            return self._empty_result()

        rule_result = self._detect_by_rules(clause_text, clause_type)
        if rule_result["risk_type"] != "none":
            return rule_result

        if not self._should_use_ai(clause_text, clause_type):
            return self._empty_result()

        ai_result = self._detect_by_ai(clause_text, clause_type)
        return self._post_process_result(ai_result, clause_text, clause_type)

    def _detect_by_rules(self, clause_text: str, clause_type: Optional[str] = None) -> Dict[str, Any]:
        text = clause_text.lower()

        if "without limitation" in text or "liable for any damages" in text:
            return {
                "risk_level": "high",
                "risk_type": "unlimited_liability",
                "reason": "The clause appears to impose liability without limitation.",
                "recommendation": "Add a liability cap and exclude indirect or consequential damages.",
                "trigger_text": "without limitation" if "without limitation" in text else "liable for any damages"
            }

        if "may terminate at any time without notice" in text:
            return {
                "risk_level": "high",
                "risk_type": "no_notice_termination",
                "reason": "The clause allows termination at any time without prior notice.",
                "recommendation": "Require advance written notice before termination.",
                "trigger_text": "may terminate at any time without notice"
            }

        if "terminate at any time" in text and "either party" not in text:
            return {
                "risk_level": "medium",
                "risk_type": "unilateral_termination",
                "reason": "The clause may allow one-sided termination.",
                "recommendation": "Clarify termination rights and require objective grounds or notice.",
                "trigger_text": "terminate at any time"
            }

        if clause_type == "termination" and "either party may terminate" in text and "written notice" in text:
            return {
                "risk_level": "none",
                "risk_type": "none",
                "reason": "The termination clause appears balanced because either party may terminate with notice.",
                "recommendation": "",
                "trigger_text": ""
            }

        if "not liable for any damages" in text:
            return {
                "risk_level": "high",
                "risk_type": "liability_exclusion",
                "reason": "The clause may fully exclude liability for damages.",
                "recommendation": "Review whether the liability exclusion is commercially acceptable.",
                "trigger_text": "not liable for any damages"
            }

        if clause_type == "governing_law" and "laws of" in text and "peru" not in text:
            return {
                "risk_level": "medium",
                "risk_type": "unfavorable_jurisdiction",
                "reason": "The clause may subject the agreement to a foreign legal jurisdiction.",
                "recommendation": "Confirm whether the governing law and forum are acceptable.",
                "trigger_text": "laws of"
            }

        if "all intellectual property rights shall belong exclusively to the client" in text:
            return {
                "risk_level": "high",
                "risk_type": "ip_transfer_broad",
                "reason": "The clause broadly transfers intellectual property rights.",
                "recommendation": "Clarify ownership of pre-existing IP and limit assignment scope.",
                "trigger_text": "all intellectual property rights shall belong exclusively to the client"
            }

        if "all intellectual property created during the course of the services shall belong to the client" in text:
            return {
                "risk_level": "high",
                "risk_type": "ip_transfer_broad",
                "reason": "The clause broadly assigns intellectual property created during the services to the client.",
                "recommendation": "Clarify ownership of pre-existing IP, background IP, and general know-how.",
                "trigger_text": "all intellectual property created during the course of the services shall belong to the client"
            }

        if "automatically renew" in text and "notice" not in text:
            return {
                "risk_level": "medium",
                "risk_type": "auto_renewal_without_notice",
                "reason": "The clause may allow automatic renewal without a clear notice mechanism.",
                "recommendation": "Add a notice period before renewal.",
                "trigger_text": "automatically renew"
            }
        
        if clause_type == "payment" and "interest at a rate of 1.5% per month" in text:
            return {
                "risk_level": "low",
                "risk_type": "excessive_penalties",
                "reason": "The late payment interest rate may be relatively high depending on the applicable jurisdiction and commercial context.",
                "recommendation": "Review whether the late payment interest rate is commercially reasonable and legally enforceable in the relevant jurisdiction.",
                "trigger_text": "interest at a rate of 1.5% per month"
            }

        return self._empty_result()

    def _should_use_ai(self, clause_text: str, clause_type: Optional[str]) -> bool:
        text = clause_text.lower()

        if clause_type in self.CRITICAL_CLAUSE_TYPES:
            return True

        return any(keyword in text for keyword in self.SUSPICIOUS_KEYWORDS)

    def _detect_by_ai(self, clause_text: str, clause_type: Optional[str]) -> Dict[str, Any]:
        prompt = PromptFramework.build_risk_prompt(
            clause_text=clause_text,
            clause_type=clause_type,
            allowed_risk_types=self.VALID_RISK_TYPES
        )

        try:
            response = self.ai.generate(prompt, temperature=0)
            data = self._parse_json_response(response)
            return self._normalize_result(data)
        except Exception:
            return self._empty_result()

    def _post_process_result(
        self,
        result: Dict[str, Any],
        clause_text: str,
        clause_type: Optional[str]
    ) -> Dict[str, Any]:
        text = clause_text.lower()

        if (
            clause_type == "termination"
            and result.get("risk_type") == "unilateral_termination"
            and "either party" in text
        ):
            return {
                "risk_level": "none",
                "risk_type": "none",
                "reason": "The clause allows termination for either party, so it is not unilateral.",
                "recommendation": "",
                "trigger_text": ""
            }

        return result

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        if not response or not response.strip():
            raise ValueError("Empty AI response")

        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if fenced_match:
            return json.loads(fenced_match.group(1))

        object_match = re.search(r"\{.*\}", response, re.DOTALL)
        if object_match:
            return json.loads(object_match.group(0))

        raise ValueError("Unable to extract valid JSON from AI response")

    def _normalize_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        risk_level = str(data.get("risk_level", "none")).strip().lower()
        risk_type = str(data.get("risk_type", "none")).strip()
        reason = str(data.get("reason", "")).strip()
        recommendation = str(data.get("recommendation", "")).strip()
        trigger_text = str(data.get("trigger_text", "")).strip()

        if risk_level not in self.VALID_RISK_LEVELS:
            risk_level = "none"

        if risk_type not in self.VALID_RISK_TYPES:
            risk_type = "other"

        return {
            "risk_level": risk_level,
            "risk_type": risk_type,
            "reason": reason,
            "recommendation": recommendation,
            "trigger_text": trigger_text
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "risk_level": "none",
            "risk_type": "none",
            "reason": "",
            "recommendation": "",
            "trigger_text": ""
        }