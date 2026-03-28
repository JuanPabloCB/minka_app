from __future__ import annotations

import json
from typing import Any

from app.core.openai_client import get_openai_client

from .types import (
    ContractUnit,
    GapCandidate,
    GapCandidateVerdict,
    LLMClauseVerdict,
    TokenUsage,
)


class LLMClauseVerifier:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.client = get_openai_client()
        self.model = model

    def _safe_json_loads(self, text: str) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {}

        try:
            return json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except Exception:
                    return {}
            return {}

    def _extract_usage(self, response: Any) -> TokenUsage:
        usage = getattr(response, "usage", None)
        if not usage:
            return TokenUsage()

        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", input_tokens + output_tokens) or 0)

        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    def _build_prompt(
        self,
        batch: list[ContractUnit],
        formal_clauses: list[ContractUnit],
        full_text: str,
    ) -> str:
        formal_refs = [
            {
                "segment_id": c.segment_id,
                "ordinal_rank": c.ordinal_rank,
                "title_guess": c.title_guess,
                "header_status": c.header_status,
            }
            for c in formal_clauses
        ]

        units = []
        for unit in batch:
            left = max(0, unit.start_index - 180)
            right = min(len(full_text), unit.end_index + 180)
            units.append(
                {
                    "segment_id": unit.segment_id,
                    "level": unit.level,
                    "title_guess": unit.title_guess,
                    "hierarchy_id": unit.hierarchy_id,
                    "parent_segment_id": unit.parent_segment_id,
                    "parent_ordinal_rank": unit.parent_ordinal_rank,
                    "focus_text": full_text[unit.start_index:unit.end_index][:900],
                    "left_context": full_text[left:unit.start_index],
                    "right_context": full_text[unit.end_index:right],
                    "header_status": unit.header_status,
                }
            )

        return f"""
Eres un verificador estructural de contratos.

Objetivo:
Clasificar unidades hijas ambiguas (subcláusulas o ítems), SIN inventar cláusulas madre nuevas.

REGLAS DURAS:
- NO conviertas una unidad en cláusula madre si no trae encabezado real explícito.
- Una referencia interna a "Cláusula X del presente contrato" NO crea una cláusula nueva.
- Si la unidad tiene jerarquía explícita tipo 21.4, respétala.
- Si la evidencia no es suficiente, usa "keep_possible".
- Devuelve SOLO JSON válido.

DECISIONES PERMITIDAS:
- accept_subclause
- keep_possible
- downgrade_to_list_item
- reject
- reparent

FORMATO:
{{
  "verdicts": [
    {{
      "segment_id": "string",
      "decision": "accept_subclause|keep_possible|downgrade_to_list_item|reject|reparent",
      "normalized_level": "subclause|list_item",
      "normalized_parent_rank": 21,
      "normalized_hierarchy_id": "21.4",
      "normalized_title": "21.4. Inexistencia de relación laboral",
      "is_valid_clause_unit": true,
      "reason": "string"
    }}
  ]
}}

CLAUSULAS_MADRE_CONFIRMADAS:
{json.dumps(formal_refs, ensure_ascii=False, indent=2)}

UNIDADES_A_VERIFICAR:
{json.dumps(units, ensure_ascii=False, indent=2)}
""".strip()

    def verify_units(
        self,
        units: list[ContractUnit],
        formal_clauses: list[ContractUnit],
        full_text: str,
        batch_size: int = 10,
    ) -> tuple[list[LLMClauseVerdict], TokenUsage]:
        all_verdicts: list[LLMClauseVerdict] = []
        usage = TokenUsage()

        if not units:
            return all_verdicts, usage

        for i in range(0, len(units), batch_size):
            batch = units[i:i + batch_size]
            prompt = self._build_prompt(batch=batch, formal_clauses=formal_clauses, full_text=full_text)

            response = self.client.responses.create(
                model=self.model,
                input=prompt,
            )

            usage.add(self._extract_usage(response))

            output_text = getattr(response, "output_text", "") or ""
            parsed = self._safe_json_loads(output_text)
            raw_verdicts = parsed.get("verdicts", []) if isinstance(parsed, dict) else []

            for item in raw_verdicts:
                all_verdicts.append(
                    LLMClauseVerdict(
                        segment_id=str(item.get("segment_id", "")).strip(),
                        decision=str(item.get("decision", "reject")).strip(),
                        normalized_level=item.get("normalized_level"),
                        normalized_parent_rank=item.get("normalized_parent_rank"),
                        normalized_hierarchy_id=item.get("normalized_hierarchy_id"),
                        normalized_title=item.get("normalized_title"),
                        is_valid_clause_unit=bool(item.get("is_valid_clause_unit", True)),
                        reason=item.get("reason"),
                    )
                )

        return all_verdicts, usage

    def apply_verdicts_to_candidates(
        self,
        possible_units: list[ContractUnit],
        verdicts: list[LLMClauseVerdict],
    ) -> tuple[list[ContractUnit], list[ContractUnit]]:
        verdict_map = {v.segment_id: v for v in verdicts}

        accepted_units: list[ContractUnit] = []
        needs_review_units: list[ContractUnit] = []

        for unit in possible_units:
            verdict = verdict_map.get(unit.segment_id)

            if not verdict:
                unit.review_status = "needs_review"
                unit.confidence_tier = "low"
                needs_review_units.append(unit)
                continue

            decision = verdict.decision.strip().lower()

            if decision == "reject":
                unit.review_status = "rejected"
                unit.confidence_tier = "low"
                continue

            if decision == "keep_possible":
                unit.review_status = "needs_review"
                unit.confidence_tier = "low"
                if verdict.reason:
                    unit.reason_hint = verdict.reason
                needs_review_units.append(unit)
                continue

            # en esta versión vendible NO aceptamos cláusulas madre por LLM
            if decision == "accept_main_clause":
                unit.review_status = "needs_review"
                unit.confidence_tier = "low"
                unit.reason_hint = verdict.reason or "No se aceptan cláusulas madre recuperadas en modo vendible."
                needs_review_units.append(unit)
                continue

            if decision == "accept_subclause":
                unit.level = "subclause"
                unit.source = "llm_verified_subclause"
                unit.confidence_tier = "medium"
                unit.review_status = "auto_accepted"

            elif decision == "downgrade_to_list_item":
                unit.level = "list_item"
                unit.source = "llm_downgraded_list_item"
                unit.confidence_tier = "medium"
                unit.review_status = "auto_accepted"

            elif decision == "reparent":
                unit.source = "llm_reparented"
                unit.confidence_tier = "medium"
                unit.review_status = "auto_accepted"

            if verdict.normalized_level:
                unit.level = verdict.normalized_level

            if verdict.normalized_title:
                unit.title_guess = str(verdict.normalized_title).strip()

            if verdict.normalized_hierarchy_id:
                unit.hierarchy_id = str(verdict.normalized_hierarchy_id).strip().lower()

            if verdict.normalized_parent_rank is not None:
                try:
                    unit.parent_ordinal_rank = int(verdict.normalized_parent_rank)
                except (TypeError, ValueError):
                    pass

            unit.reviewed_by_llm = True
            if verdict.reason:
                unit.reason_hint = verdict.reason

            accepted_units.append(unit)

        return accepted_units, needs_review_units

    # Compatibilidad: sin recuperación por gaps en modo vendible
    def verify_gap_candidates(
        self,
        gaps: list[GapCandidate],
        batch_size: int = 6,
    ) -> tuple[list[GapCandidateVerdict], TokenUsage]:
        return [], TokenUsage()

    def apply_gap_verdicts(
        self,
        gaps: list[GapCandidate],
        verdicts: list[GapCandidateVerdict],
    ) -> tuple[list[ContractUnit], list[ContractUnit]]:
        return [], []