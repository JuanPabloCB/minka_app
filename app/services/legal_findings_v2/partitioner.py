from __future__ import annotations

import re

from .parser import ClauseParser
from .types import ClauseDetectionPartition, ContractUnit


class ClausePartitioner:
    def __init__(self, parser: ClauseParser) -> None:
        self.parser = parser

    def _infer_explicit_hierarchy_id(self, unit: ContractUnit) -> str:
        candidates = [
            str(unit.hierarchy_id or "").strip(),
            str(unit.title_guess or "").strip(),
            str(unit.text or "").strip()[:160],
        ]

        patterns = [
            r"^\s*(\d+(?:\.\d+){2,})\b",
            r"^\s*(\d+\.(?:\d+|[a-z]+))\b",
        ]

        for value in candidates:
            for pattern in patterns:
                m = re.match(pattern, value, flags=re.IGNORECASE)
                if m:
                    return m.group(1).strip().lower()

        return ""

    def _is_strong_explicit_hierarchy_id(self, hierarchy_id: str) -> bool:
        hid = str(hierarchy_id or "").strip().lower()
        return bool(
            re.match(r"^\d+\.(?:\d+|[a-z]+)$", hid, flags=re.IGNORECASE)
            or re.match(r"^\d+(?:\.\d+){2,}$", hid, flags=re.IGNORECASE)
        )

    def partition_units_for_clause_detection(
        self,
        contract_units: dict[str, list[ContractUnit]],
    ) -> ClauseDetectionPartition:
        trusted_units: list[ContractUnit] = []
        llm_candidates: list[ContractUnit] = []
        rejected_units: list[ContractUnit] = []

        for unit in contract_units.get("all_units", []):
            level = unit.level.strip().lower()
            hierarchy_id = self._infer_explicit_hierarchy_id(unit)

            if level == "formal_clause":
                if unit.header_status == "formal_header_explicit":
                    unit.confidence_tier = "high"
                    unit.review_status = "auto_accepted"
                    trusted_units.append(unit)
                elif unit.header_status == "cross_reference_only":
                    unit.confidence_tier = "low"
                    unit.review_status = "rejected"
                    rejected_units.append(unit)
                else:
                    # no confirmamos cláusulas madre ambiguas en esta versión
                    unit.confidence_tier = "low"
                    unit.review_status = "needs_review"
                    llm_candidates.append(unit)
                continue

            if level == "subclause":
                if self._is_strong_explicit_hierarchy_id(hierarchy_id):
                    unit.hierarchy_id = hierarchy_id
                    unit.confidence_tier = "high"
                    unit.review_status = "auto_accepted"
                    trusted_units.append(unit)
                else:
                    unit.confidence_tier = "medium"
                    unit.review_status = "needs_review"
                    llm_candidates.append(unit)
                continue

            if level == "list_item":
                if hierarchy_id and self._is_strong_explicit_hierarchy_id(hierarchy_id):
                    unit.hierarchy_id = hierarchy_id
                    unit.confidence_tier = "medium"
                    unit.review_status = "needs_review"
                    llm_candidates.append(unit)
                else:
                    unit.confidence_tier = "low"
                    unit.review_status = "rejected"
                    rejected_units.append(unit)
                continue

            unit.review_status = "rejected"
            rejected_units.append(unit)

        trusted_units = sorted(trusted_units, key=lambda u: (u.start_index, u.level))
        llm_candidates = sorted(llm_candidates, key=lambda u: (u.start_index, u.level))
        rejected_units = sorted(rejected_units, key=lambda u: (u.start_index, u.level))

        return ClauseDetectionPartition(
            trusted_units=trusted_units,
            llm_candidates=llm_candidates,
            rejected_units=rejected_units,
        )