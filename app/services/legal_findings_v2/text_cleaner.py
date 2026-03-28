from __future__ import annotations

import re


class LegalTextCleaner:
    _STOPWORDS = {
        "de", "del", "la", "las", "el", "los", "y", "o", "u",
        "a", "al", "en", "por", "para", "con", "sin", "que",
        "se", "su", "sus", "un", "una", "unos", "unas",
    }

    def clean(self, text: str) -> str:
        if not text:
            return ""

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = self._remove_page_number_lines(text)
        text = self._remove_inline_page_noise(text)
        text = self._fix_short_ocr_word_splits(text)
        text = self._normalize_spacing(text)
        return text.strip()

    def _remove_page_number_lines(self, text: str) -> str:
        lines = text.splitlines()
        kept: list[str] = []

        for line in lines:
            stripped = line.strip()

            if re.fullmatch(r"\d{1,3}", stripped):
                continue

            if re.fullmatch(r"(p[áa]g(?:ina)?\.?)\s*\d{1,3}", stripped, flags=re.IGNORECASE):
                continue

            kept.append(line)

        return "\n".join(kept)

    def _remove_inline_page_noise(self, text: str) -> str:
        # "... Contrato. 3 b)" -> "... Contrato. b)"
        text = re.sub(r"(?<=\.)\s+\d{1,3}\s+(?=[a-z]\)|[a-z]\.)", " ", text, flags=re.IGNORECASE)

        # "... anuales. 17" al final de línea -> quitar 17
        text = re.sub(r"(?m)([A-Za-zÁÉÍÓÚÑáéíóúñ\)\.])\s+\d{1,3}\s*$", r"\1", text)

        return text

    def _fix_short_ocr_word_splits(self, text: str) -> str:
        """
        Conservador:
        - une solo palabras claramente partidas por OCR
        - evita unir frases normales tipo 'de acuerdo'
        """
        pattern = re.compile(
            r"\b([A-Za-zÁÉÍÓÚÑáéíóúñ]{1,3})\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]{3,})\b"
        )

        def repl(match: re.Match[str]) -> str:
            left = match.group(1)
            right = match.group(2)

            if left.lower() in self._STOPWORDS:
                return match.group(0)

            # P arte / uti lización / g arantía / int erpretación
            return f"{left}{right}"

        prev = None
        current = text
        for _ in range(3):
            if current == prev:
                break
            prev = current
            current = pattern.sub(repl, current)

        return current

    def _normalize_spacing(self, text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" ?([,;:.])", r"\1", text)
        text = re.sub(r"([,;:.])([^\s\n])", r"\1 \2", text)
        return text