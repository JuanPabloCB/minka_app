import re
from typing import List, Dict


class DocumentStructureAnalyzer:
    """
    Detects structural hierarchy in legal documents such as:
    sections, subsections, and numbered clauses.
    """

    SECTION_PATTERNS = [
        r"^\d+\.\s",          # 1.
        r"^\d+\.\d+\s",       # 1.1
        r"^\d+\.\d+\.\d+\s",  # 1.1.1
        r"^Section\s+\d+",    # Section 2
        r"^Article\s+[IVX]+"  # Article IV
    ]

    def detect_structure(self, text: str) -> List[Dict]:

        lines = text.split("\n")

        structure = []

        for line in lines:

            cleaned = line.strip()

            if not cleaned:
                continue

            level = self._detect_level(cleaned)

            if level is not None:

                structure.append({
                    "title": cleaned,
                    "level": level
                })

        return structure

    def _detect_level(self, line: str):

        if re.match(r"^\d+\.\d+\.\d+\s", line):
            return 3

        if re.match(r"^\d+\.\d+\s", line):
            return 2

        if re.match(r"^\d+\.\s", line):
            return 1

        if re.match(r"^Section\s+\d+", line, re.IGNORECASE):
            return 1

        if re.match(r"^Article\s+[IVX]+", line, re.IGNORECASE):
            return 1

        return None