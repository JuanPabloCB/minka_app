import re
from typing import List, Dict, Optional


class ClauseSegmenter:
    """
    Robust legal clause segmenter for digital contracts.

    Strategy:
    1. Split the document into logical non-empty lines.
    2. Detect likely clause headings using multiple structural heuristics.
    3. Group text from one heading until the next heading.
    4. Merge orphan headings with the following content when necessary.
    5. Fallback to full-document single clause if no valid structure is found.

    This version is more resilient to:
    - numbered headings
    - section/article headings
    - uppercase clause titles
    - short standalone headings followed by body text
    - mixed formatting in contracts
    """

    NUMBERED_HEADING_RE = re.compile(
        r"""(?ix)
        ^
        (
            \d+\.\d+\.\d+      |   # 1.1.1
            \d+\.\d+           |   # 1.1
            \d+\.              |   # 1.
            section\s+\d+      |   # Section 2
            article\s+[ivxlcdm]+ | # Article IV
            clause\s+\d+           # Clause 3
        )
        (\s+|$)
        """
    )

    UPPERCASE_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9\s\-/&,()]{3,}$")
    TITLE_CASE_HEADING_RE = re.compile(r"^[A-Z][A-Za-z0-9\s\-/&,()]{2,80}$")

    EXCLUDED_HEADINGS = {
        "table of contents",
        "contents",
        "signature",
        "signatures",
        "execution",
    }

    MIN_CLAUSE_LENGTH = 40
    MAX_HEADING_LENGTH = 120
    MAX_HEADING_WORDS = 12

    def segment(self, text: str) -> List[Dict]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        cleaned_text = self._normalize_document_text(text)
        if not cleaned_text:
            return []

        lines = self._split_non_empty_lines(cleaned_text)
        if not lines:
            return []

        heading_indexes = self._detect_heading_indexes(lines)

        if not heading_indexes:
            return self._fallback_single_clause(cleaned_text)

        grouped_blocks = self._group_blocks_by_headings(lines, heading_indexes)
        clauses = self._build_clauses(grouped_blocks)

        if not clauses:
            return self._fallback_single_clause(cleaned_text)

        return clauses

    def _normalize_document_text(self, text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _split_non_empty_lines(self, text: str) -> List[str]:
        raw_lines = text.split("\n")
        lines = [line.strip() for line in raw_lines if line.strip()]
        return lines

    def _detect_heading_indexes(self, lines: List[str]) -> List[int]:
        indexes: List[int] = []

        for i, line in enumerate(lines):
            previous_line = lines[i - 1] if i > 0 else None
            next_line = lines[i + 1] if i + 1 < len(lines) else None

            if self._is_heading_candidate(line, previous_line, next_line):
                indexes.append(i)

        return self._deduplicate_heading_indexes(indexes)

    def _is_heading_candidate(
        self,
        line: str,
        previous_line: Optional[str],
        next_line: Optional[str],
    ) -> bool:
        candidate = line.strip()
        if not candidate:
            return False

        lowered = candidate.lower()
        if lowered in self.EXCLUDED_HEADINGS:
            return False

        if len(candidate) > self.MAX_HEADING_LENGTH:
            return False

        word_count = len(candidate.split())
        if word_count > self.MAX_HEADING_WORDS:
            return False

        if self.NUMBERED_HEADING_RE.match(candidate):
            return True

        if self._looks_like_uppercase_heading(candidate, next_line):
            return True

        if self._looks_like_short_title_heading(candidate, previous_line, next_line):
            return True

        return False

    def _looks_like_uppercase_heading(self, line: str, next_line: Optional[str]) -> bool:
        if not self.UPPERCASE_HEADING_RE.match(line):
            return False

        if next_line is None:
            return False

        # Stronger signal if next line looks like sentence body text
        return self._looks_like_body_text(next_line)

    def _looks_like_short_title_heading(
        self,
        line: str,
        previous_line: Optional[str],
        next_line: Optional[str],
    ) -> bool:
        if not self.TITLE_CASE_HEADING_RE.match(line):
            return False

        if line.endswith("."):
            return False

        if next_line is None:
            return False

        if not self._looks_like_body_text(next_line):
            return False

        # Avoid treating ordinary body lines as headings
        if self._looks_like_body_text(line):
            return False

        # Stronger if isolated from previous body flow
        if previous_line and self._looks_like_body_text(previous_line):
            return False

        return True

    def _looks_like_body_text(self, line: str) -> bool:
        stripped = line.strip()

        if len(stripped) < 25:
            return False

        # Sentence-like signals
        if stripped.endswith(".") or stripped.endswith(";") or stripped.endswith(":"):
            return True

        lower_count = sum(1 for ch in stripped if ch.islower())
        upper_count = sum(1 for ch in stripped if ch.isupper())

        return lower_count > upper_count

    def _deduplicate_heading_indexes(self, indexes: List[int]) -> List[int]:
        if not indexes:
            return []

        deduped = [indexes[0]]

        for idx in indexes[1:]:
            if idx != deduped[-1]:
                deduped.append(idx)

        return deduped

    def _group_blocks_by_headings(self, lines: List[str], heading_indexes: List[int]) -> List[Dict]:
        blocks: List[Dict] = []

        for pos, start_idx in enumerate(heading_indexes):
            end_idx = heading_indexes[pos + 1] if pos + 1 < len(heading_indexes) else len(lines)

            block_lines = lines[start_idx:end_idx]
            if not block_lines:
                continue

            title = block_lines[0].strip()
            body_lines = block_lines[1:]

            # If the block only contains a heading and no body, keep it for possible merge
            blocks.append({
                "title": title,
                "lines": block_lines,
                "body_lines": body_lines,
            })

        return self._merge_orphan_headings(blocks)

    def _merge_orphan_headings(self, blocks: List[Dict]) -> List[Dict]:
        """
        If a heading block has almost no content, merge it into the next block when sensible.
        """
        if not blocks:
            return []

        merged: List[Dict] = []
        i = 0

        while i < len(blocks):
            current = blocks[i]
            current_text = self._join_lines(current["lines"])

            if (
                len(current["body_lines"]) == 0
                or len(current_text) < self.MIN_CLAUSE_LENGTH
            ) and i + 1 < len(blocks):
                nxt = blocks[i + 1]

                combined_lines = current["lines"] + nxt["lines"]
                merged.append({
                    "title": current["title"],
                    "lines": combined_lines,
                    "body_lines": combined_lines[1:],
                })
                i += 2
                continue

            merged.append(current)
            i += 1

        return merged

    def _build_clauses(self, blocks: List[Dict]) -> List[Dict]:
        clauses: List[Dict] = []

        for block in blocks:
            text = self._join_lines(block["lines"])
            text = self._normalize_clause_text(text)

            if len(text) < self.MIN_CLAUSE_LENGTH:
                continue

            clauses.append({
                "clause_id": len(clauses) + 1,
                "title": block["title"],
                "text": text,
            })

        return clauses

    def _join_lines(self, lines: List[str]) -> str:
        return "\n".join(line.strip() for line in lines if line.strip())

    def _fallback_single_clause(self, text: str) -> List[Dict]:
        normalized = self._normalize_clause_text(text)

        if len(normalized) < self.MIN_CLAUSE_LENGTH:
            return []

        return [{
            "clause_id": 1,
            "title": "Full Document",
            "text": normalized,
        }]

    def _normalize_clause_text(self, text: str) -> str:
        normalized = text.strip()
        normalized = re.sub(r"\n{2,}", "\n", normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        return normalized