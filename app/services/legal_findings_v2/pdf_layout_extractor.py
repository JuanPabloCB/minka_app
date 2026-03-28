from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

import pdfplumber

from .types import DocumentLayout, PdfLine


class PdfLayoutExtractor:
    """
    Extrae layout real desde PDF usando palabras y reconstrucción por líneas.

    Objetivos:
    - preservar mejor encabezados partidos
    - obtener bbox reales por línea
    - reducir ruido de cabeceras / pies repetidos
    - producir full_text alineado con lines/global_start/global_end
    """

    def __init__(
        self,
        y_tolerance: float = 3.0,
        x_tolerance: float = 2.0,
        header_footer_band: float = 72.0,
    ) -> None:
        self.y_tolerance = y_tolerance
        self.x_tolerance = x_tolerance
        self.header_footer_band = header_footer_band

    # ------------------------------------------------------------------
    # Normalización y ruido
    # ------------------------------------------------------------------
    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    def _normalize_for_repetition(self, text: str) -> str:
        clean = self._normalize_spaces(text).lower()
        clean = re.sub(r"\b(pág\.?|pag\.?|page)\s*\d+\b", "PAGE_NUM", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\b\d+\b", "NUM", clean)
        return clean.strip()

    def _is_trivial_noise(self, text: str) -> bool:
        clean = self._normalize_spaces(text)
        if not clean:
            return True

        lower = clean.lower()

        # solo número o paginación
        if re.match(r"^\d{1,4}$", clean):
            return True

        if re.match(r"^(pág\.?|pag\.?|page)\s*\d{1,4}$", lower, flags=re.IGNORECASE):
            return True

        # basura típica
        if lower in {
            "copia no controlada",
            "anexo",
            "apéndice",
            "apendice",
        }:
            return True

        # líneas muy cortas y no informativas
        if len(clean) <= 1:
            return True

        return False

    def _looks_like_header_or_footer_zone(
        self,
        top: float,
        bottom: float,
        page_height: float,
    ) -> bool:
        return top <= self.header_footer_band or bottom >= (page_height - self.header_footer_band)

    # ------------------------------------------------------------------
    # Palabras -> líneas
    # ------------------------------------------------------------------
    def _group_words_into_lines(
        self,
        words: list[dict[str, Any]],
        page_height: float,
    ) -> list[dict[str, Any]]:
        if not words:
            return []

        # ordenar por top y luego x0
        sorted_words = sorted(
            words,
            key=lambda w: (
                round(float(w.get("top", 0.0)), 1),
                float(w.get("x0", 0.0)),
            ),
        )

        raw_lines: list[list[dict[str, Any]]] = []
        current_line: list[dict[str, Any]] = []
        current_top: float | None = None

        for word in sorted_words:
            text = self._normalize_spaces(str(word.get("text", "")))
            if not text:
                continue

            top = float(word.get("top", 0.0))

            if current_top is None:
                current_line = [word]
                current_top = top
                continue

            if abs(top - current_top) <= self.y_tolerance:
                current_line.append(word)
            else:
                if current_line:
                    raw_lines.append(current_line)
                current_line = [word]
                current_top = top

        if current_line:
            raw_lines.append(current_line)

        result: list[dict[str, Any]] = []

        for line_words in raw_lines:
            line_words = sorted(line_words, key=lambda w: float(w.get("x0", 0.0)))

            parts: list[str] = []
            prev_x1: float | None = None

            for w in line_words:
                token = self._normalize_spaces(str(w.get("text", "")))
                if not token:
                    continue

                x0 = float(w.get("x0", 0.0))

                if prev_x1 is None:
                    parts.append(token)
                else:
                    gap = x0 - prev_x1
                    # si están pegados, no metas espacio extra artificial
                    if gap <= self.x_tolerance:
                        parts.append(token)
                    else:
                        parts.append(" " + token)

                prev_x1 = float(w.get("x1", 0.0))

            line_text = "".join(parts)
            line_text = self._normalize_spaces(line_text)

            if not line_text:
                continue

            x0 = min(float(w.get("x0", 0.0)) for w in line_words)
            x1 = max(float(w.get("x1", 0.0)) for w in line_words)
            top = min(float(w.get("top", 0.0)) for w in line_words)
            bottom = max(float(w.get("bottom", 0.0)) for w in line_words)

            result.append(
                {
                    "text": line_text,
                    "x0": x0,
                    "x1": x1,
                    "top": top,
                    "bottom": bottom,
                    "page_height": page_height,
                }
            )

        return result

    # ------------------------------------------------------------------
    # Fallback cuando extract_words no devuelve suficiente
    # ------------------------------------------------------------------
    def _fallback_lines_from_extract_text(
        self,
        page: pdfplumber.page.Page,
        page_idx: int,
    ) -> list[dict[str, Any]]:
        raw_text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
        page_lines: list[dict[str, Any]] = []

        for line_idx, raw_line in enumerate(raw_text.splitlines(), start=1):
            line = self._normalize_spaces(raw_line)
            if not line:
                continue

            page_lines.append(
                {
                    "page_num": page_idx,
                    "text": line,
                    "x0": 0.0,
                    "x1": float(page.width),
                    "top": float(line_idx * 12),
                    "bottom": float(line_idx * 12 + 10),
                    "page_height": float(page.height),
                }
            )

        return page_lines

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------
    def extract(self, pdf_path: str) -> DocumentLayout:
        raw_page_lines: list[dict[str, Any]] = []
        page_count = 0

        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)

            for page_idx, page in enumerate(pdf.pages, start=1):
                words = page.extract_words(
                    x_tolerance=self.x_tolerance,
                    y_tolerance=self.y_tolerance,
                    keep_blank_chars=False,
                    use_text_flow=True,
                ) or []

                if words:
                    grouped_lines = self._group_words_into_lines(
                        words=words,
                        page_height=float(page.height),
                    )

                    for item in grouped_lines:
                        raw_page_lines.append(
                            {
                                "page_num": page_idx,
                                "text": item["text"],
                                "x0": item["x0"],
                                "x1": item["x1"],
                                "top": item["top"],
                                "bottom": item["bottom"],
                                "page_height": item["page_height"],
                            }
                        )
                else:
                    raw_page_lines.extend(self._fallback_lines_from_extract_text(page, page_idx))

        # --------------------------------------------------------------
        # Detectar cabeceras / pies repetidos entre páginas
        # --------------------------------------------------------------
        repeated_candidates: list[str] = []

        for item in raw_page_lines:
            text = self._normalize_spaces(item["text"])
            if not text:
                continue

            if self._looks_like_header_or_footer_zone(
                top=float(item["top"]),
                bottom=float(item["bottom"]),
                page_height=float(item["page_height"]),
            ):
                repeated_candidates.append(self._normalize_for_repetition(text))

        repeated_counter = Counter(repeated_candidates)

        # si aparece en muchas páginas y está arriba/abajo, es boilerplate
        repeated_boilerplate: set[str] = {
            key
            for key, count in repeated_counter.items()
            if count >= max(3, math.ceil(page_count * 0.4))
        }

        # --------------------------------------------------------------
        # Filtrado final + armado de PdfLine con global offsets reales
        # --------------------------------------------------------------
        lines: list[PdfLine] = []
        text_parts: list[str] = []
        cursor = 0
        page_line_counters: dict[int, int] = {}

        for item in raw_page_lines:
            text = self._normalize_spaces(item["text"])
            if self._is_trivial_noise(text):
                continue

            normalized_rep = self._normalize_for_repetition(text)
            in_header_footer_zone = self._looks_like_header_or_footer_zone(
                top=float(item["top"]),
                bottom=float(item["bottom"]),
                page_height=float(item["page_height"]),
            )

            if in_header_footer_zone and normalized_rep in repeated_boilerplate:
                continue

            page_num = int(item["page_num"])
            page_line_counters[page_num] = page_line_counters.get(page_num, 0) + 1

            start = cursor
            text_parts.append(text)
            cursor += len(text)
            end = cursor
            text_parts.append("\n")
            cursor += 1

            lines.append(
                PdfLine(
                    page_num=page_num,
                    line_index=page_line_counters[page_num],
                    text=text,
                    x0=float(item["x0"]),
                    top=float(item["top"]),
                    x1=float(item["x1"]),
                    bottom=float(item["bottom"]),
                    global_start=start,
                    global_end=end,
                )
            )

        full_text = "".join(text_parts).strip()

        return DocumentLayout(
            full_text=full_text,
            lines=lines,
            page_count=page_count,
        )