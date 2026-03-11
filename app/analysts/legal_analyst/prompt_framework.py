from textwrap import dedent
from typing import Iterable, Optional


class PromptFramework:
    """
    Internal prompt engineering helper for Minka Legal Analyst.
    """

    @staticmethod
    def build_classifier_prompt(clause_text: str, allowed_types: Iterable[str]) -> str:
        allowed_types_str = "\n".join(allowed_types)

        return dedent(f"""
        ROLE:
        You are a legal contract clause classification engine.

        OBJECTIVE:
        Classify the input clause into exactly one semantic category.

        ALLOWED CATEGORIES:
        {allowed_types_str}

        DECISION RULES:
        1. Choose exactly one category.
        2. Prefer the most specific legal meaning over a generic interpretation.
        3. Use "other" only if none of the listed categories clearly apply.
        4. Confidence must be a number between 0 and 1.
        5. Return valid JSON only.
        6. Do not include markdown, explanations, or extra text.

        OUTPUT CONTRACT:
        {{
          "type": "<category>",
          "confidence": <number between 0 and 1>
        }}

        INPUT CLAUSE:
        <<<CLAUSE_START>>>
        {clause_text}
        <<<CLAUSE_END>>>
        """).strip()

    @staticmethod
    def build_risk_prompt(
        clause_text: str,
        clause_type: Optional[str],
        allowed_risk_types: Iterable[str]
    ) -> str:
        allowed_risk_types_str = "\n".join(allowed_risk_types)
        clause_type = clause_type or "unknown"

        return dedent(f"""
        ROLE:
        You are a legal contract risk analysis engine.

        OBJECTIVE:
        Determine whether the input clause presents a contractual legal risk.

        CONTEXT:
        Clause semantic type: {clause_type}

        ALLOWED RISK TYPES:
        {allowed_risk_types_str}

        DECISION RULES:
        1. Return "none" only if no meaningful contractual risk is present.
        2. Use "high" for strong, explicit, materially adverse legal language.
        3. Use "medium" for materially concerning but not absolute language.
        4. Use "low" for mild or ambiguous concern.
        5. trigger_text must contain an exact risky phrase or a short literal fragment from the clause.
        6. If no specific trigger exists, return an empty string for trigger_text.
        7. Return valid JSON only.
        8. Do not include markdown, code fences, explanations outside JSON, or commentary.

        OUTPUT CONTRACT:
        {{
          "risk_level": "none|low|medium|high",
          "risk_type": "none|unlimited_liability|unilateral_termination|no_notice_termination|unfavorable_jurisdiction|ip_transfer_broad|broad_indemnification|payment_ambiguity|one_sided_confidentiality|excessive_penalties|auto_renewal_without_notice|liability_exclusion|other",
          "reason": "short explanation",
          "recommendation": "short recommendation",
          "trigger_text": "exact risky phrase or short literal fragment"
        }}

        INPUT CLAUSE:
        <<<CLAUSE_START>>>
        {clause_text}
        <<<CLAUSE_END>>>
        """).strip()