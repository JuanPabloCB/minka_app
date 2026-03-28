from __future__ import annotations

import re

from .types import ContractUnit


class ClauseTreeValidator:
    def _is_strong_explicit_hierarchy_id(self, hierarchy_id: str) -> bool:
        hid = str(hierarchy_id or "").strip().lower()
        return bool(
            re.match(r"^\d+\.(?:\d+|[a-z]+)$", hid, flags=re.IGNORECASE)
            or re.match(r"^\d+(?:\.\d+){2,}$", hid, flags=re.IGNORECASE)
        )

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

    def _looks_like_normative_list_item(self, unit: ContractUnit) -> bool:
        text = re.sub(r"\s+", " ", (unit.text or "").strip()).lower()
        title = re.sub(r"\s+", " ", (unit.title_guess or "").strip()).lower()
        hierarchy_id = self._infer_explicit_hierarchy_id(unit)

        target = f"{title} {text}".strip()
        raw_text = (unit.text or "").strip()

        normative_keywords = [
            "ley",
            "reglamento",
            "decreto",
            "resolución",
            "resolucion",
            "osiptel",
            "ministerio",
            "código civil",
            "codigo civil",
            "disposiciones complementarias",
            "texto único ordenado",
            "texto unico ordenado",
            "lineamientos",
            "normas aplicables",
            "marco normativo",
        ]

        starts_like_list = bool(
            re.match(r"^\s*(\d+\.|[a-z]\)|[ivxlcdm]+\))\s+", raw_text, flags=re.IGNORECASE)
        )

        if self._is_strong_explicit_hierarchy_id(hierarchy_id):
            starts_like_list = False

        if starts_like_list and any(keyword in target for keyword in normative_keywords):
            return True

        if re.match(r"^\d+\.\s+", raw_text) and any(keyword in target for keyword in normative_keywords):
            return True

        return False

    def _title_keyword_overlap_score(self, unit_text: str, formal_title: str) -> int:
        text = re.sub(r"\s+", " ", (unit_text or "").strip()).lower()
        title = re.sub(r"\s+", " ", (formal_title or "").strip()).lower()

        stopwords = {
            "cláusula", "clausula", "de", "del", "la", "las", "los", "y", "en",
            "para", "el", "a", "por", "con", "que", "se", "al", "o",
        }

        title_terms = [
            token for token in re.findall(r"[a-záéíóúñ]{4,}", title)
            if token not in stopwords
        ]

        score = 0
        for token in title_terms:
            if token in text:
                score += 1

        return score

    def _normalize_child_body_for_dedupe(self, unit: ContractUnit) -> str:
        text = re.sub(r"\s+", " ", (unit.text or "").strip()).lower()
        hierarchy_id = self._infer_explicit_hierarchy_id(unit)

        if hierarchy_id:
            text = re.sub(rf"^\s*{re.escape(hierarchy_id)}[\.\)]?\s*", "", text)

        title_guess = re.sub(r"\s+", " ", (unit.title_guess or "").strip()).lower()
        if title_guess and text.startswith(title_guess[:100]):
            text = text[len(title_guess[:100]):].strip()

        return text[:220]

    def _child_dedupe_score(self, unit: ContractUnit) -> tuple:
        hierarchy_id = self._infer_explicit_hierarchy_id(unit)
        parent_rank = unit.parent_ordinal_rank

        parent_matches_hierarchy = 1
        if self._is_strong_explicit_hierarchy_id(hierarchy_id):
            top_rank = int(hierarchy_id.split(".", 1)[0])
            if parent_rank is not None and int(parent_rank) == top_rank:
                parent_matches_hierarchy = 0

        return (
            0 if hierarchy_id else 1,
            parent_matches_hierarchy,
            0 if unit.source in {"llm_verified_subclause", "llm_reparented"} else 1,
            len((unit.title_guess or "").strip()),
            -len((unit.text or "").strip()),
            unit.start_index,
        )

    def _dedupe_formal_clauses_by_rank(self, formal_clauses: list[ContractUnit]) -> list[ContractUnit]:
        grouped: dict[int, list[ContractUnit]] = {}
        passthrough: list[ContractUnit] = []

        for clause in formal_clauses:
            if clause.ordinal_rank is None:
                passthrough.append(clause)
                continue
            grouped.setdefault(int(clause.ordinal_rank), []).append(clause)

        result: list[ContractUnit] = []
        for _, items in grouped.items():
            items = sorted(
                items,
                key=lambda x: (
                    0 if x.header_status == "formal_header_explicit" else 1,
                    0 if x.confidence_tier == "high" else 1,
                    x.start_index,
                    -len(x.text or ""),
                ),
            )
            result.append(items[0])

        result.extend(passthrough)
        return sorted(result, key=lambda x: x.start_index)

    def reparent_by_nearest_formal_context(
        self,
        formal_clauses: list[ContractUnit],
        units: list[ContractUnit],
    ) -> list[ContractUnit]:
        if not formal_clauses or not units:
            return units

        formal_sorted = sorted(formal_clauses, key=lambda x: x.start_index)
        updated: list[ContractUnit] = []

        for unit in units:
            hierarchy_id = self._infer_explicit_hierarchy_id(unit)

            if self._is_strong_explicit_hierarchy_id(hierarchy_id):
                updated.append(unit)
                continue

            if self._looks_like_normative_list_item(unit):
                unit.level = "list_item"
                updated.append(unit)
                continue

            previous_formal: ContractUnit | None = None
            next_formal: ContractUnit | None = None

            for clause in formal_sorted:
                if clause.start_index <= unit.start_index:
                    previous_formal = clause
                elif clause.start_index > unit.start_index:
                    next_formal = clause
                    break

            candidates = [c for c in (previous_formal, next_formal) if c is not None]
            if not candidates:
                updated.append(unit)
                continue

            best_clause: ContractUnit | None = None
            best_score: tuple | None = None

            for clause in candidates:
                distance = abs(unit.start_index - clause.start_index)
                overlap_score = self._title_keyword_overlap_score(unit.text, clause.title_guess)

                score = (
                    -overlap_score,
                    distance,
                    clause.start_index,
                )

                if best_score is None or score < best_score:
                    best_score = score
                    best_clause = clause

            if best_clause is not None:
                unit.parent_segment_id = best_clause.segment_id
                unit.parent_ordinal_rank = best_clause.ordinal_rank

            updated.append(unit)

        return updated

    def validate(self, units: list[ContractUnit]) -> dict[str, list[ContractUnit]]:
        formal_candidates = [u for u in units if u.level == "formal_clause"]
        other_units = [u for u in units if u.level != "formal_clause"]

        cleaned_formal_candidates: list[ContractUnit] = []
        for clause in formal_candidates:
            title = re.sub(r"\s+", " ", (clause.title_guess or "").strip()).lower()
            text = re.sub(r"\s+", " ", (clause.text or "").strip()[:220]).lower()

            if clause.ordinal_rank is None:
                continue

            if not (clause.text or "").strip():
                continue

            if clause.header_status != "formal_header_explicit":
                continue

            if clause.header_status == "cross_reference_only":
                continue

            if "del presente contrato" in title or "del presente contrato" in text:
                continue

            if re.search(r"(?i)\b(previstas?|establecidas?|señaladas?|indicadas?)\s+en\s+la\b", text):
                continue

            cleaned_formal_candidates.append(clause)

        formal_clauses = self._dedupe_formal_clauses_by_rank(cleaned_formal_candidates)
        formal_clauses = sorted(formal_clauses, key=lambda x: x.start_index)

        rank_to_parent_id: dict[int, str] = {}
        for idx, clause in enumerate(formal_clauses, start=1):
            clause.segment_id = f"C-{idx:03d}"
            if clause.ordinal_rank is not None:
                rank_to_parent_id[int(clause.ordinal_rank)] = clause.segment_id

        remapped: list[ContractUnit] = []
        for unit in other_units:
            hid = self._infer_explicit_hierarchy_id(unit)
            if hid:
                unit.hierarchy_id = hid

            target_rank = None

            if self._is_strong_explicit_hierarchy_id(hid):
                target_rank = int(hid.split(".", 1)[0])
            elif unit.parent_ordinal_rank is not None:
                target_rank = int(unit.parent_ordinal_rank)

            if target_rank is None:
                remapped.append(unit)
                continue

            parent_id = rank_to_parent_id.get(target_rank)
            if not parent_id:
                remapped.append(unit)
                continue

            unit.parent_segment_id = parent_id
            unit.parent_ordinal_rank = target_rank
            remapped.append(unit)

        remapped = self.reparent_by_nearest_formal_context(formal_clauses, remapped)

        for unit in remapped:
            if unit.level == "subclause" and self._looks_like_normative_list_item(unit):
                unit.level = "list_item"

        valid_parent_ids = {c.segment_id for c in formal_clauses}
        cleaned_children: list[ContractUnit] = []

        for unit in remapped:
            if not unit.parent_segment_id:
                continue
            if unit.parent_segment_id not in valid_parent_ids:
                continue
            cleaned_children.append(unit)

        seen_children: dict[tuple, ContractUnit] = {}
        for unit in sorted(
            cleaned_children,
            key=lambda x: (x.start_index, x.level, x.hierarchy_id or "")
        ):
            key = (
                unit.level,
                self._infer_explicit_hierarchy_id(unit),
                self._normalize_child_body_for_dedupe(unit),
            )

            previous = seen_children.get(key)
            if previous is None or self._child_dedupe_score(unit) < self._child_dedupe_score(previous):
                seen_children[key] = unit

        deduped_children = list(seen_children.values())

        counters: dict[str, int] = {}
        for unit in sorted(
            deduped_children,
            key=lambda x: (x.start_index, x.level, x.hierarchy_id or "")
        ):
            parent_id = unit.parent_segment_id
            if not parent_id:
                continue

            counters[parent_id] = counters.get(parent_id, 0) + 1

            if unit.level == "subclause":
                prefix = "S"
            elif unit.level == "list_item":
                prefix = "L"
            else:
                prefix = "X"

            unit.segment_id = f"{parent_id}-{prefix}{counters[parent_id]:02d}"

        subclauses = [u for u in deduped_children if u.level == "subclause"]
        list_items = [u for u in deduped_children if u.level == "list_item"]

        all_units = formal_clauses + subclauses + list_items
        all_units = sorted(all_units, key=lambda x: (x.start_index, x.level, x.hierarchy_id or ""))

        return {
            "formal_clauses": formal_clauses,
            "subclauses": subclauses,
            "list_items": list_items,
            "all_units": all_units,
        }