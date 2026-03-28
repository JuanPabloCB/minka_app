from __future__ import annotations

import re

from .parser import ClauseParser
from .types import ContractUnit, DocumentLayout, GapCandidate


class CandidateBuilder:
    def __init__(self, parser: ClauseParser) -> None:
        self.parser = parser

    def _guess_title(self, text: str, max_len: int = 180) -> str:
        clean = re.sub(r"\s+", " ", (text or "").strip())
        return clean[:max_len]

    def _extract_local_marker(self, text: str) -> str | None:
        t = (text or "").strip()
        patterns = [
            r"^\s*(\d{1,3}(?:\.\d{1,3})+)(?:\.)?\s+",
            r"^\s*([a-z])\)\s+",
            r"^\s*([a-z])\.\s+",
            r"^\s*(\d{1,3})\)\s+",
            r"^\s*(\d{1,3})\.\s+(?!\d)",
            r"^\s*([ivxlcdm]+)\)\s+",
        ]
        for pattern in patterns:
            m = re.match(pattern, t, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _compose_hierarchy_id(
        self,
        parent_rank: int | None,
        local_marker: str | None,
    ) -> str | None:
        if not local_marker:
            return None

        marker = local_marker.strip()

        if re.match(r"^\d+(?:\.\d+)+$", marker):
            return marker

        if parent_rank is None:
            return marker.lower()

        if re.match(r"^\d+$", marker):
            return f"{parent_rank}.{marker}"

        if re.match(r"^[a-z]$", marker, flags=re.IGNORECASE):
            return f"{parent_rank}.{marker.lower()}"

        if re.match(r"^[ivxlcdm]+$", marker, flags=re.IGNORECASE):
            return f"{parent_rank}.{marker.lower()}"

        return marker.lower()

    def _looks_like_bad_fragment(self, text: str) -> bool:
        raw = (text or "").strip()
        if not raw:
            return True

        lower = re.sub(r"\s+", " ", raw).strip().lower()
        word_count = len(re.findall(r"\b\w+\b", lower))

        if word_count < 6:
            return True

        if re.match(r"^(según|conforme a|de conformidad con|previstas? en)\s+la\s+cláusula\b", lower):
            return True

        if re.match(r"^\d+\)\s*(días|dia|mes|meses|años)\b", lower):
            return True

        return False

    def _looks_like_informative_list_item(self, text: str) -> bool:
        raw = (text or "").strip()
        if not raw:
            return False

        lower = re.sub(r"\s+", " ", raw).strip().lower()

        if re.match(r"^\s*\d+\.\s+", raw) and len(lower) < 300:
            if any(k in lower for k in ["ley", "reglamento", "decreto", "resolución", "resolucion", "osiptel"]):
                return True

        if re.match(r"^\s*([ivxlcdm]+|\d+|[a-z])\)\s+", raw, flags=re.IGNORECASE):
            if len(lower) < 220 and not re.search(r"\bdeber[aá]|podr[aá]|se obliga|tendr[aá] derecho\b", lower):
                return True

        return False

    def _extract_formal_clauses_from_headers(
        self,
        full_text: str,
        headers: list[dict[str, object]],
        source_name: str,
    ) -> list[ContractUnit]:
        clauses: list[ContractUnit] = []
        if not headers:
            return clauses

        sorted_headers = sorted(headers, key=lambda h: int(h["start_index"]))

        for idx, header in enumerate(sorted_headers, start=1):
            start = int(header["start_index"])
            next_start = (
                int(sorted_headers[idx]["start_index"])
                if idx < len(sorted_headers)
                else len(full_text)
            )

            raw_block = full_text[start:next_start].strip()
            raw_block = self.parser.truncate_at_next_formal_clause_header(raw_block)

            if len(raw_block) < 40:
                continue

            header_text = str(header["header_text"]).strip()
            ordinal_rank = self.parser.extract_ordinal_rank_from_header(header_text)
            header_status = self.parser.classify_header_status(header_text)

            if header_status != "formal_header_explicit":
                continue

            real_end = start + len(raw_block)

            extra: dict[str, object] = {}
            if "page_num" in header:
                extra["page_num"] = header["page_num"]
            if "line_index" in header:
                extra["line_index"] = header["line_index"]

            clauses.append(
                ContractUnit(
                    segment_id=f"TMP-C-{idx:03d}",
                    level="formal_clause",
                    title_guess=self._guess_title(header_text),
                    text=raw_block,
                    source=source_name,
                    start_index=start,
                    end_index=real_end,
                    ordinal_rank=ordinal_rank,
                    header_status=header_status,
                    confidence_tier="high",
                    review_status="auto_accepted",
                    extra=extra,
                )
            )

        return clauses

    def _extract_formal_clauses(self, text: str) -> list[ContractUnit]:
        headers = self.parser.find_formal_header_lines(text)
        return self._extract_formal_clauses_from_headers(
            full_text=text,
            headers=headers,
            source_name="formal_clause",
        )

    def _extract_formal_clauses_from_layout(self, layout: DocumentLayout) -> list[ContractUnit]:
        headers = self.parser.find_formal_header_lines_from_layout(layout)
        return self._extract_formal_clauses_from_headers(
            full_text=layout.full_text,
            headers=headers,
            source_name="formal_clause_layout",
        )

    def extract_section_blocks_inside_clause_four(self, clause: ContractUnit) -> list[ContractUnit]:
        if clause.ordinal_rank != 4:
            return []

        pattern = re.compile(
            r"(?im)^\s*([a-d])\.\s+(TELEF[ÓO]NICA|EL OPERADOR)\b[^\n]*$"
        )

        matches = list(pattern.finditer(clause.text or ""))
        units: list[ContractUnit] = []

        for idx, match in enumerate(matches, start=1):
            start = match.start()
            end = matches[idx].start() if idx < len(matches) else len(clause.text or "")

            raw_part = (clause.text or "")[start:end].strip()
            if len(raw_part) < 40:
                continue

            section_letter = match.group(1).lower()
            hierarchy_id = f"4.{section_letter}"

            units.append(
                ContractUnit(
                    segment_id=f"{clause.segment_id}-TMP-SEC{idx:02d}",
                    parent_segment_id=clause.segment_id,
                    level="subclause",
                    title_guess=self._guess_title(raw_part),
                    text=raw_part,
                    source="section_block_rule_based",
                    start_index=clause.start_index + start,
                    end_index=clause.start_index + start + len(raw_part),
                    parent_ordinal_rank=4,
                    hierarchy_id=hierarchy_id,
                    local_marker=section_letter,
                    confidence_tier="high",
                    review_status="auto_accepted",
                )
            )

        return units

    def _extract_subclauses_from_formal_clause(self, clause: ContractUnit) -> list[ContractUnit]:
        text = clause.text or ""
        parent_rank = clause.ordinal_rank
        parent_id = clause.segment_id

        if clause.ordinal_rank == 4:
            section_units = self.extract_section_blocks_inside_clause_four(clause)
            if section_units:
                return section_units

        combined = re.compile(
            r"|".join(
                [
                    r"(?:^\s*(\d{1,3}(?:\.\d{1,3})+)(?:\.)?\s+)",
                    r"(?:^\s*([a-z])\)\s+)",
                    r"(?:^\s*([a-z])\.\s+)",
                    r"(?:^\s*(\d{1,3})\)\s+)",
                    r"(?:^\s*(\d{1,3})\.\s+(?!\d))",
                    r"(?:^\s*([ivxlcdm]+)\)\s+)",
                ]
            ),
            re.IGNORECASE | re.MULTILINE,
        )

        matches = list(combined.finditer(text))
        units: list[ContractUnit] = []

        for idx, match in enumerate(matches, start=1):
            start = match.start()
            end = matches[idx].start() if idx < len(matches) else len(text)

            raw_part = text[start:end].strip()
            raw_part = self.parser.truncate_at_next_formal_clause_header(raw_part)

            if len(raw_part) < 35:
                continue
            if self._looks_like_bad_fragment(raw_part):
                continue

            local_marker = self._extract_local_marker(raw_part)
            hierarchy_id = self._compose_hierarchy_id(parent_rank=parent_rank, local_marker=local_marker)
            level = "list_item" if self._looks_like_informative_list_item(raw_part) else "subclause"

            units.append(
                ContractUnit(
                    segment_id=f"{parent_id}-TMP-S{idx:02d}",
                    parent_segment_id=parent_id,
                    level=level,
                    title_guess=self._guess_title(raw_part),
                    text=raw_part,
                    source="subclause_rule_based" if level == "subclause" else "list_item_rule_based",
                    start_index=clause.start_index + start,
                    end_index=clause.start_index + start + len(raw_part),
                    parent_ordinal_rank=parent_rank,
                    hierarchy_id=hierarchy_id,
                    local_marker=local_marker,
                    confidence_tier="high" if hierarchy_id else "medium",
                    review_status="auto_accepted" if hierarchy_id else "needs_review",
                )
            )

        return units

    def _assemble_units(self, formal_clauses: list[ContractUnit]) -> dict[str, list[ContractUnit]]:
        subclauses: list[ContractUnit] = []
        list_items: list[ContractUnit] = []

        for clause in formal_clauses:
            children = self._extract_subclauses_from_formal_clause(clause)
            for child in children:
                if child.level == "subclause":
                    subclauses.append(child)
                elif child.level == "list_item":
                    list_items.append(child)

        all_units = formal_clauses + subclauses + list_items
        all_units = sorted(
            all_units,
            key=lambda u: (u.start_index, u.level, u.hierarchy_id or ""),
        )

        return {
            "formal_clauses": formal_clauses,
            "subclauses": subclauses,
            "list_items": list_items,
            "all_units": all_units,
        }

    def build_contract_units(self, text: str) -> dict[str, list[ContractUnit]]:
        formal_clauses = self._extract_formal_clauses(text)
        return self._assemble_units(formal_clauses)

    def build_contract_units_from_layout(self, layout: DocumentLayout) -> dict[str, list[ContractUnit]]:
        formal_clauses = self._extract_formal_clauses_from_layout(layout)
        return self._assemble_units(formal_clauses)

    # Compatibilidad: en esta versión vendible no recuperamos cláusulas madre por gaps.
    def build_gap_candidates(
        self,
        formal_clauses: list[ContractUnit],
        text: str,
    ) -> list[GapCandidate]:
        return []

    def build_gap_candidates_from_layout(
        self,
        formal_clauses: list[ContractUnit],
        layout: DocumentLayout,
    ) -> list[GapCandidate]:
        return []