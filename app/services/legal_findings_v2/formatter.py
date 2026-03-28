from __future__ import annotations

import hashlib
import re
from typing import Any

from .types import (
    ClauseDetectionResult,
    ClauseDetectionSummary,
    ContractUnit,
    TokenUsage,
)


class FindingsFormatter:
    def _make_stable_hash(self, *parts: Any) -> str:
        raw = "||".join("" if p is None else str(p) for p in parts)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]

    def _level_priority(self, level: str) -> int:
        order = {
            "formal_clause": 0,
            "subclause": 1,
            "list_item": 2,
        }
        return order.get(level or "", 9)

    def _normalize_findings(self, units: list[ContractUnit]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        confidence_by_level = {
            "formal_clause": 0.98,
            "subclause": 0.95,
            "list_item": 0.70,
        }

        category_by_level = {
            "formal_clause": "formal_clause",
            "subclause": "functional_clause",
            "list_item": "list_item",
        }

        default_reason_by_level = {
            "formal_clause": "Cláusula formal detectada por encabezado o recuperación estructural.",
            "subclause": "Subcláusula detectada dentro de una cláusula principal.",
            "list_item": "Ítem detectado dentro de una enumeración contractual.",
        }

        for unit in units:
            excerpt = re.sub(r"\s+", " ", (unit.text or "").strip())[:300]
            stable_id = f"F-{self._make_stable_hash(unit.level, unit.segment_id, unit.hierarchy_id, excerpt[:120])}"

            title_value = (unit.title_guess or "").strip() or "Unidad contractual detectada"
            reason_value = unit.reason_hint or default_reason_by_level.get(unit.level, "Unidad contractual detectada.")

            findings.append(
                {
                    "finding_id": stable_id,
                    "title": title_value[:180],
                    "category": category_by_level.get(unit.level, "other_clause"),
                    "confidence": confidence_by_level.get(unit.level, 0.50),
                    "excerpt": excerpt,
                    "reason": reason_value,
                    "segment_id": unit.segment_id,
                    "parent_segment_id": unit.parent_segment_id,
                    "title_guess": unit.title_guess,
                    "level": unit.level,
                    "hierarchy_id": unit.hierarchy_id,
                    "source": unit.source,
                    "start_index": unit.start_index,
                    "end_index": unit.end_index,
                    "header_status": getattr(unit, "header_status", "not_applicable"),
                    "confidence_tier": getattr(unit, "confidence_tier", "unknown"),
                    "review_status": getattr(unit, "review_status", "auto_accepted"),
                }
            )

        return findings

    def _deduplicate_findings(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple] = set()
        result: list[dict[str, Any]] = []

        for f in findings:
            level = f.get("level")
            segment_id = f.get("segment_id")
            parent_segment_id = f.get("parent_segment_id")
            hierarchy_id = f.get("hierarchy_id")
            title = (f.get("title") or f.get("title_guess") or "").strip().lower()
            excerpt = (f.get("excerpt") or "").strip().lower()
            header_status = f.get("header_status")

            if level == "formal_clause":
                key = (
                    level,
                    segment_id,
                    title[:180],
                    header_status,
                )
            else:
                key = (
                    level,
                    parent_segment_id,
                    hierarchy_id,
                    excerpt[:220],
                )

            if key in seen:
                continue

            seen.add(key)
            result.append(f)

        return result

    def _sort_findings(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            findings,
            key=lambda f: (
                int(f.get("start_index", 10**9)),
                self._level_priority(f.get("level", "")),
                str(f.get("hierarchy_id") or ""),
            ),
        )

    def _normalize_review_units(self, units: list[ContractUnit]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for unit in units:
            items.append(
                {
                    "segment_id": unit.segment_id,
                    "title_guess": unit.title_guess,
                    "level": unit.level,
                    "ordinal_rank": unit.ordinal_rank,
                    "hierarchy_id": unit.hierarchy_id,
                    "source": unit.source,
                    "header_status": getattr(unit, "header_status", "not_applicable"),
                    "confidence_tier": getattr(unit, "confidence_tier", "unknown"),
                    "review_status": getattr(unit, "review_status", "needs_review"),
                    "excerpt": re.sub(r"\s+", " ", (unit.text or "").strip())[:250],
                    "reason": unit.reason_hint,
                }
            )
        return items

    def format_result(
        self,
        validated_units: dict[str, list[ContractUnit]],
        appendix_text: str,
        token_usage: TokenUsage,
        possible_main_clauses: list[ContractUnit],
        missing_expected_ranks: list[int],
    ) -> ClauseDetectionResult:
        confirmed_main_clauses = validated_units.get("formal_clauses", [])
        subclauses = validated_units.get("subclauses", [])
        list_items = validated_units.get("list_items", [])

        findings = self._normalize_findings(
            confirmed_main_clauses + possible_main_clauses + subclauses + list_items
        )
        findings = self._deduplicate_findings(findings)
        findings = self._sort_findings(findings)

        needs_review = self._normalize_review_units(
            [u for u in possible_main_clauses if getattr(u, "review_status", "") == "needs_review"]
        )

        summary = ClauseDetectionSummary(
            confirmed_main_clause_count=len(confirmed_main_clauses),
            possible_main_clause_count=len(possible_main_clauses),
            formal_clause_count=len(confirmed_main_clauses) + len(possible_main_clauses),
            subclause_count=len(subclauses),
            list_item_count=len(list_items),
            atomic_provision_count=0,
            total_contract_units=(
                len(confirmed_main_clauses)
                + len(possible_main_clauses)
                + len(subclauses)
                + len(list_items)
            ),
            appendix_length=len(appendix_text or ""),
        )

        return ClauseDetectionResult(
            formal_clauses=confirmed_main_clauses,
            confirmed_main_clauses=confirmed_main_clauses,
            possible_main_clauses=possible_main_clauses,
            subclauses=subclauses,
            list_items=list_items,
            findings=findings,
            summary=summary,
            appendix_text=appendix_text,
            token_usage=token_usage,
            missing_expected_ranks=missing_expected_ranks,
            needs_review=needs_review,
        )