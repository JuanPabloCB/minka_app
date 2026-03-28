from __future__ import annotations

import re
from typing import Any, Pattern

from .types import DocumentLayout


ORDINAL_RANK_MAP: dict[str, int] = {
    "primera": 1,
    "segunda": 2,
    "tercera": 3,
    "cuarta": 4,
    "quinta": 5,
    "sexta": 6,
    "séptima": 7,
    "septima": 7,
    "setima": 7,
    "octava": 8,
    "novena": 9,
    "décima": 10,
    "decima": 10,
    "décima primera": 11,
    "decima primera": 11,
    "décima segunda": 12,
    "decima segunda": 12,
    "décima tercera": 13,
    "decima tercera": 13,
    "décima cuarta": 14,
    "decima cuarta": 14,
    "décima quinta": 15,
    "decima quinta": 15,
    "décima sexta": 16,
    "decima sexta": 16,
    "décima séptima": 17,
    "decima séptima": 17,
    "decima septima": 17,
    "decima setima": 17,
    "décima octava": 18,
    "decima octava": 18,
    "décima novena": 19,
    "decima novena": 19,
    "vigésima": 20,
    "vigesima": 20,
    "vigésima primera": 21,
    "vigesima primera": 21,
    "vigésima segunda": 22,
    "vigesima segunda": 22,
    "vigésima tercera": 23,
    "vigesima tercera": 23,
    "vigésima cuarta": 24,
    "vigesima cuarta": 24,
    "vigésima quinta": 25,
    "vigesima quinta": 25,
    "vigésima sexta": 26,
    "vigesima sexta": 26,
    "vigésima séptima": 27,
    "vigesima séptima": 27,
    "vigesima septima": 27,
    "vigesima setima": 27,
    "vigésima octava": 28,
    "vigesima octava": 28,
    "vigésima novena": 29,
    "vigesima novena": 29,
    "trigésima": 30,
    "trigesima": 30,
}


class ClauseParser:
    """
    Parser robusto para detectar encabezados de cláusulas madre.

    Soporta:
    - CLÁUSULA PRIMERA: OBJETO
    - CLÁUSULA 1: OBJETO
    - CLÁUSULA N° 1: OBJETO
    - ARTÍCULO PRIMERO: OBJETO
    - ARTÍCULO 1: OBJETO
    - SECCIÓN 1: OBJETO
    - 1. OBJETO
    - 1 OBJETO

    Mantiene compatibilidad con candidate_builder.py y pipeline.py actuales.
    """

    def __init__(self) -> None:
        # Se conserva por compatibilidad, pero truncate_at_next_formal_clause_header
        # ya no depende exclusivamente de este regex.
        self._formal_header_pattern = self._build_formal_clause_header_regex()

    # -------------------------------------------------------------------------
    # Regex de compatibilidad
    # -------------------------------------------------------------------------
    def _build_formal_clause_header_regex(self) -> Pattern[str]:
        return re.compile(
            r"(?im)^\s*(?:"
            r"cl[áa]usula|art[íi]culo|secci[óo]n"
            r")\b[^\n]*$"
        )

    def formal_clause_header_regex(self) -> Pattern[str]:
        return self._formal_header_pattern

    # -------------------------------------------------------------------------
    # Limpieza básica
    # -------------------------------------------------------------------------
    def clean_extracted_text(self, text: str) -> str:
        if not text:
            return ""

        cleaned = text.replace("\r", "\n")

        replacements = {
            "": "L",
            "": "I",
            "": "A",
            "": "O",
            "": "E",
            "": "U",
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
            "\u00a0": " ",
        }

        for bad, good in replacements.items():
            cleaned = cleaned.replace(bad, good)

        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return cleaned.strip()

    def split_main_body_and_appendices(self, text: str) -> tuple[str, str]:
        if not text:
            return "", ""

        appendix_pattern = re.compile(r"(?im)^\s*(ap[ée]ndice|apendice|anexo)\b")
        match = appendix_pattern.search(text)
        if not match:
            return text.strip(), ""

        return text[:match.start()].strip(), text[match.start():].strip()

    def extract_line_blocks(self, text: str) -> list[dict[str, int | str]]:
        lines = text.splitlines()
        blocks: list[dict[str, int | str]] = []
        cursor = 0

        for raw in lines:
            line = raw.rstrip("\n")
            start = cursor
            end = cursor + len(raw)
            blocks.append(
                {
                    "text": line,
                    "start_index": start,
                    "end_index": end,
                }
            )
            cursor = end + 1

        return blocks

    # -------------------------------------------------------------------------
    # Helpers internos
    # -------------------------------------------------------------------------
    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    def _lower(self, text: str) -> str:
        return self._normalize_spaces(text).lower()

    def _upper_ratio(self, text: str) -> float:
        letters = [ch for ch in text if ch.isalpha()]
        if not letters:
            return 0.0
        return sum(1 for ch in letters if ch.isupper()) / len(letters)

    def _looks_like_page_noise(self, line: str) -> bool:
        clean = self._normalize_spaces(line)
        if not clean:
            return True

        if re.match(r"^\d{1,4}$", clean):
            return True

        if re.match(r"^(página|pagina)\s+\d{1,4}$", clean, flags=re.IGNORECASE):
            return True

        return False

    def _looks_like_header_continuation(self, line: str) -> bool:
        clean = self._normalize_spaces(line)
        if not clean:
            return False

        if len(clean) > 140:
            return False

        # si termina con punto/; suele parecer más cuerpo que continuación de título
        if re.search(r"[.;]\s*$", clean):
            return False

        # continuación heading-like: bastante mayúscula o bien "de/para/y ..."
        upper_ratio = self._upper_ratio(clean)
        if upper_ratio >= 0.55:
            return True

        if re.match(
            r"^(de|del|de la|de las|de los|para|y|sobre|entre|con|sin)\b",
            clean,
            flags=re.IGNORECASE,
        ):
            return True

        return False

    def _starts_like_reference_phrase(self, text: str) -> bool:
        clean = self._lower(text)
        return bool(
            re.match(
                r"^(del|de la|de las|de los|conforme|según|segun|previstas?|"
                r"establecidas?|señaladas?|indicadas?)\b",
                clean,
            )
        )

    def _extract_rank_from_words(self, text: str) -> int | None:
        clean = self._lower(text)
        for key, value in sorted(ORDINAL_RANK_MAP.items(), key=lambda kv: len(kv[0]), reverse=True):
            if clean.startswith(key):
                return value
        return None

    def _extract_tail_after_word_rank(self, text: str) -> tuple[int | None, str]:
        clean = self._normalize_spaces(text)
        lower = clean.lower()

        for key, value in sorted(ORDINAL_RANK_MAP.items(), key=lambda kv: len(kv[0]), reverse=True):
            if lower.startswith(key):
                tail = clean[len(key):].strip(" .:-–—")
                return value, tail

        return None, ""

    def _extract_header_components(self, line: str) -> tuple[str | None, int | None, str]:
        """
        Devuelve:
        - kind
        - rank
        - tail/title

        kind puede ser:
        - formal_clause_word
        - formal_clause_numeric
        - article_word
        - article_numeric
        - section_numeric
        - bare_numeric
        """
        clean = self._normalize_spaces(line)
        if not clean:
            return None, None, ""

        # -------------------------------------------------
        # 1) CLÁUSULA / ARTÍCULO / SECCIÓN + número explícito
        # -------------------------------------------------
        m = re.match(
            r"^(cl[áa]usula|art[íi]culo|secci[óo]n)\s*(?:n[°ºo]\.?\s*)?(\d{1,3})\b(?:\s*[:.\-–—]\s*|\s+)(.+)$",
            clean,
            flags=re.IGNORECASE,
        )
        if m:
            leader = m.group(1).lower()
            rank = int(m.group(2))
            tail = self._normalize_spaces(m.group(3)).strip(" .:-–—")
            if "cl" in leader:
                return "formal_clause_numeric", rank, tail
            if "art" in leader:
                return "article_numeric", rank, tail
            return "section_numeric", rank, tail

        # -------------------------------------------------
        # 2) CLÁUSULA / ARTÍCULO + ordinal en palabras
        # -------------------------------------------------
        m = re.match(
            r"^(cl[áa]usula|art[íi]culo)\s+(.+)$",
            clean,
            flags=re.IGNORECASE,
        )
        if m:
            leader = m.group(1).lower()
            rest = self._normalize_spaces(m.group(2))
            rank, tail = self._extract_tail_after_word_rank(rest)
            if rank is not None:
                if "cl" in leader:
                    return "formal_clause_word", rank, tail
                return "article_word", rank, tail

        # -------------------------------------------------
        # 3) Encabezado numérico pelado: 1. OBJETO / 1 OBJETO
        # -------------------------------------------------
        m = re.match(
            r"^(\d{1,3})(?:\.)?\s+(.+)$",
            clean,
            flags=re.IGNORECASE,
        )
        if m:
            rank = int(m.group(1))
            tail = self._normalize_spaces(m.group(2)).strip(" .:-–—")
            if self._looks_like_bare_numeric_heading_tail(tail):
                return "bare_numeric", rank, tail

        return None, None, ""

    def _looks_like_bare_numeric_heading_tail(self, tail: str) -> bool:
        """
        Muy importante para no confundir:
        - 1. OBJETO                      -> sí
        - 1. Texto Único Ordenado ...    -> no (list item normativo)
        """
        clean = self._normalize_spaces(tail)
        lower = clean.lower()

        if not clean:
            return False

        if len(clean) < 3 or len(clean) > 140:
            return False

        # No frases claramente de cuerpo
        if re.match(r"^(las|los|el|la|se|por|para|cuando|si|en|deberá|debera|podrá|podra)\b", lower):
            return False

        # Si parece ítem normativo / bibliográfico, rechazar
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
            "texto único ordenado",
            "texto unico ordenado",
            "disposiciones complementarias",
        ]
        if any(k in lower for k in normative_keywords):
            return False

        word_count = len(re.findall(r"\b\w+\b", clean))
        upper_ratio = self._upper_ratio(clean)

        # heading pelado normalmente no debería ser larguísimo
        if word_count > 14 and upper_ratio < 0.70:
            return False

        # si termina en punto y no es muy heading-like, rechazar
        if clean.endswith(".") and upper_ratio < 0.70:
            return False

        # Aceptamos si:
        # - está muy heading-like por mayúsculas
        # - o es corto y limpio
        if upper_ratio >= 0.45:
            return True

        if word_count <= 6 and not self._starts_like_reference_phrase(clean):
            return True

        return False

    def _extract_rank_generic(self, header_text: str) -> int | None:
        _, rank, _ = self._extract_header_components(header_text)
        return rank

    def _extract_tail_generic(self, header_text: str) -> str:
        _, _, tail = self._extract_header_components(header_text)
        return tail

    # -------------------------------------------------------------------------
    # API pública usada por otros módulos
    # -------------------------------------------------------------------------
    def extract_ordinal_rank_from_header(self, header_text: str) -> int | None:
        return self._extract_rank_generic(header_text)

    def is_real_header_line(self, line: str) -> bool:
        clean = self._normalize_spaces(line)
        if not clean:
            return False

        if self._looks_like_page_noise(clean):
            return False

        clean_lower = clean.lower()

        # referencias internas típicas
        if "del presente contrato" in clean_lower:
            return False

        if re.search(r"\b(previstas?|establecidas?|señaladas?|indicadas?)\s+en\s+la\b", clean, flags=re.IGNORECASE):
            return False

        kind, rank, tail = self._extract_header_components(clean)

        if kind is None or rank is None:
            return False

        if not tail:
            return False

        if len(tail) < 3:
            return False

        if self._starts_like_reference_phrase(tail):
            return False

        return True

    def is_cross_reference_only(self, text: str) -> bool:
        clean = self._normalize_spaces(text)
        if not clean:
            return False

        if self.is_real_header_line(clean):
            return False

        # referencia tipo "Cláusula Décima Séptima."
        if re.match(
            r"^(cl[áa]usula|art[íi]culo)\s+(?:n[°ºo]\.?\s*)?(?:\d{1,3}|[a-záéíóúñ ]+)[\.\:]?$",
            clean,
            flags=re.IGNORECASE,
        ):
            return True

        # referencia embebida
        if re.search(
            r"\b(cl[áa]usula|art[íi]culo)\s+(?:n[°ºo]\.?\s*)?(?:\d{1,3}|[a-záéíóúñ ]+)\b",
            clean,
            flags=re.IGNORECASE,
        ):
            return True

        return False

    def classify_header_status(self, text: str) -> str:
        if self.is_real_header_line(text):
            return "formal_header_explicit"

        if self.is_cross_reference_only(text):
            return "cross_reference_only"

        return "unknown"

    # -------------------------------------------------------------------------
    # Detección de encabezados en texto plano
    # -------------------------------------------------------------------------
    def find_formal_header_lines(self, text: str) -> list[dict[str, int | str]]:
        lines = self.extract_line_blocks(text)
        headers: list[dict[str, int | str]] = []

        for idx, block in enumerate(lines):
            line = str(block["text"]).strip()
            if not line or self._looks_like_page_noise(line):
                continue

            # 1 línea
            if self.is_real_header_line(line):
                headers.append(
                    {
                        "header_text": line,
                        "start_index": int(block["start_index"]),
                        "end_index": int(block["end_index"]),
                    }
                )
                continue

            # 2 líneas
            if idx + 1 < len(lines):
                next_line = str(lines[idx + 1]["text"]).strip()
                if next_line and self._looks_like_header_continuation(next_line):
                    combined_2 = f"{line} {next_line}".strip()
                    if self.is_real_header_line(combined_2):
                        headers.append(
                            {
                                "header_text": combined_2,
                                "start_index": int(block["start_index"]),
                                "end_index": int(lines[idx + 1]["end_index"]),
                            }
                        )
                        continue

            # 3 líneas
            if idx + 2 < len(lines):
                next_line = str(lines[idx + 1]["text"]).strip()
                next_next_line = str(lines[idx + 2]["text"]).strip()

                if (
                    next_line
                    and next_next_line
                    and self._looks_like_header_continuation(next_line)
                    and self._looks_like_header_continuation(next_next_line)
                ):
                    combined_3 = f"{line} {next_line} {next_next_line}".strip()
                    if self.is_real_header_line(combined_3):
                        headers.append(
                            {
                                "header_text": combined_3,
                                "start_index": int(block["start_index"]),
                                "end_index": int(lines[idx + 2]["end_index"]),
                            }
                        )

        deduped: list[dict[str, int | str]] = []
        seen_starts: set[int] = set()

        for item in headers:
            start = int(item["start_index"])
            if start in seen_starts:
                continue
            seen_starts.add(start)
            deduped.append(item)

        return deduped

    # -------------------------------------------------------------------------
    # Compatibilidad para gaps (hoy no usados como recovery)
    # -------------------------------------------------------------------------
    def extract_gap_header_candidates(
        self,
        gap_text: str,
        max_candidates: int = 8,
    ) -> list[dict[str, object]]:
        lines = self.extract_line_blocks(gap_text)
        candidates: list[dict[str, object]] = []

        for idx, block in enumerate(lines):
            line = str(block["text"]).strip()
            if not line:
                continue

            local_start = int(block["start_index"])
            local_end = int(block["end_index"])

            if self.is_real_header_line(line):
                candidates.append(
                    {
                        "header_text": line,
                        "local_start_index": local_start,
                        "local_end_index": local_end,
                        "line_number": idx,
                        "source": "real_header_line",
                    }
                )
                continue

            if idx + 1 < len(lines):
                next_line = str(lines[idx + 1]["text"]).strip()
                if next_line and self._looks_like_header_continuation(next_line):
                    combined = f"{line} {next_line}".strip()
                    if self.is_real_header_line(combined):
                        candidates.append(
                            {
                                "header_text": combined,
                                "local_start_index": local_start,
                                "local_end_index": int(lines[idx + 1]["end_index"]),
                                "line_number": idx,
                                "source": "combined_header_line",
                            }
                        )

        deduped: list[dict[str, object]] = []
        seen: set[tuple[str, int]] = set()

        for item in candidates:
            key = (str(item["header_text"]).strip().lower(), int(item["local_start_index"]))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return deduped[:max_candidates]

    # -------------------------------------------------------------------------
    # Corte hasta el siguiente encabezado formal
    # -------------------------------------------------------------------------
    def truncate_at_next_formal_clause_header(self, text: str) -> str:
        raw = text or ""
        if not raw.strip():
            return ""

        headers = self.find_formal_header_lines(raw)
        if len(headers) <= 1:
            return raw.strip()

        first_start = int(headers[0]["start_index"])
        for item in headers[1:]:
            start = int(item["start_index"])
            if start > first_start:
                return raw[:start].strip()

        return raw.strip()

    # -------------------------------------------------------------------------
    # Detección desde layout
    # -------------------------------------------------------------------------
    def find_formal_header_lines_from_layout(
        self,
        layout: DocumentLayout,
    ) -> list[dict[str, Any]]:
        headers: list[dict[str, Any]] = []

        for idx, line in enumerate(layout.lines):
            current = self._normalize_spaces(line.text)
            if not current or self._looks_like_page_noise(current):
                continue

            # 1 línea
            if self.is_real_header_line(current):
                headers.append(
                    {
                        "header_text": current,
                        "page_num": line.page_num,
                        "line_index": line.line_index,
                        "start_index": line.global_start,
                        "end_index": line.global_end,
                    }
                )
                continue

            # 2 líneas
            if idx + 1 < len(layout.lines):
                nxt = self._normalize_spaces(layout.lines[idx + 1].text)
                if nxt and self._looks_like_header_continuation(nxt):
                    combined_2 = f"{current} {nxt}".strip()
                    if self.is_real_header_line(combined_2):
                        headers.append(
                            {
                                "header_text": combined_2,
                                "page_num": line.page_num,
                                "line_index": line.line_index,
                                "start_index": line.global_start,
                                "end_index": layout.lines[idx + 1].global_end,
                            }
                        )
                        continue

            # 3 líneas
            if idx + 2 < len(layout.lines):
                nxt = self._normalize_spaces(layout.lines[idx + 1].text)
                nxt2 = self._normalize_spaces(layout.lines[idx + 2].text)

                if (
                    nxt
                    and nxt2
                    and self._looks_like_header_continuation(nxt)
                    and self._looks_like_header_continuation(nxt2)
                ):
                    combined_3 = f"{current} {nxt} {nxt2}".strip()
                    if self.is_real_header_line(combined_3):
                        headers.append(
                            {
                                "header_text": combined_3,
                                "page_num": line.page_num,
                                "line_index": line.line_index,
                                "start_index": line.global_start,
                                "end_index": layout.lines[idx + 2].global_end,
                            }
                        )

        deduped: list[dict[str, Any]] = []
        seen_starts: set[int] = set()

        for item in headers:
            start = int(item["start_index"])
            if start in seen_starts:
                continue
            seen_starts.add(start)
            deduped.append(item)

        return deduped