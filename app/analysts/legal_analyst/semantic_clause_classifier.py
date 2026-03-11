from typing import Dict, Any
import json
import re

from app.core.ai_gateway import AIGateway
from app.analysts.legal_analyst.prompt_framework import PromptFramework


class SemanticClauseClassifier:
    """
    AI-based semantic classifier for legal clauses.
    Uses structured prompts and robust JSON extraction.
    """

    VALID_TYPES = [
        "payment",
        "termination",
        "liability",
        "confidentiality",
        "intellectual_property",
        "governing_law",
        "dispute_resolution",
        "force_majeure",
        "scope_of_services",
        "duration",
        "other",
    ]

    def __init__(self):
        self.ai = AIGateway()

    def classify(self, clause_text: str) -> Dict[str, Any]:
        if not isinstance(clause_text, str):
            raise TypeError("clause_text must be a string")

        clause_text = clause_text.strip()
        if not clause_text:
            return self._fallback_result("Empty clause text")

        prompt = PromptFramework.build_classifier_prompt(
            clause_text=clause_text,
            allowed_types=self.VALID_TYPES
        )

        try:
            response = self.ai.generate(prompt, temperature=0)
            data = self._parse_json_response(response)
            return self._normalize_result(data)
        except Exception as exc:
            return self._fallback_result(str(exc))

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

        raise ValueError(f"Unable to extract valid JSON from AI response: {response[:200]}")

    def _normalize_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        clause_type = str(data.get("type", "other")).strip()
        confidence = data.get("confidence", 0.0)

        if clause_type not in self.VALID_TYPES:
            clause_type = "other"

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))

        return {
            "type": clause_type,
            "confidence": confidence
        }

    def _fallback_result(self, error_message: str) -> Dict[str, Any]:
        return {
            "type": "other",
            "confidence": 0.0,
            "error": f"Classification fallback applied: {error_message}"
        }