from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from app.core.openai_client import get_openai_client
from .types import ContractUnit, TokenUsage


MODEL = "gpt-4.1-mini"


@dataclass
class RestorationCandidate:
    segment_id: str
    ordinal_rank: int | None
    start_index: int
    end_index: int
    text: str
    score: int


class SelectiveTextRestorer:
    def __init__(self, model: str = MODEL) -> None:
        self.client = get_openai_client()
        self.model = model

    def find_candidates(
        self,
        formal_clauses: list[ContractUnit],
        missing_expected_ranks: list[int],
        max_candidates: int = 8,
    ) -> list[RestorationCandidate]:
        candidates: list[RestorationCandidate] = []

        gap_neighbors: set[int] = set()
        for rank in missing_expected_ranks:
            gap_neighbors.add(rank - 1)
            gap_neighbors.add(rank + 1)

        for clause in formal_clauses:
            score = self._ocr_noise_score(clause.text or "")

            if clause.ordinal_rank in gap_neighbors:
                score += 2

            if score <= 0:
                continue

            candidates.append(
                RestorationCandidate(
                    segment_id=clause.segment_id,
                    ordinal_rank=clause.ordinal_rank,
                    start_index=clause.start_index,
                    end_index=clause.end_index,
                    text=clause.text or "",
                    score=score,
                )
            )

        candidates.sort(key=lambda x: (-x.score, x.start_index))
        return candidates[:max_candidates]

    def _ocr_noise_score(self, text: str) -> int:
        score = 0

        patterns = [
            r"\b[A-Za-zÁÉÍÓÚÑáéíóúñ]{1,3}\s+[A-Za-zÁÉÍÓÚÑáéíóúñ]{3,}\b",
            r"(?<=\.)\s+\d{1,3}\s+(?=[a-z]\)|[a-z]\.)",
            r"\bINT\s+ERPRE",
            r"\bP\s+arte\b",
            r"\buti\s+liza",
            r"\bg\s+arant",
        ]

        for pattern in patterns:
            score += len(re.findall(pattern, text, flags=re.IGNORECASE))

        return score

    def restore_candidates(
        self,
        main_body_text: str,
        candidates: list[RestorationCandidate],
    ) -> tuple[str, TokenUsage]:
        if not candidates:
            return main_body_text, TokenUsage()

        usage = TokenUsage()
        updated_text = main_body_text

        # reemplazar de atrás hacia adelante para no romper offsets
        for candidate in sorted(candidates, key=lambda x: x.start_index, reverse=True):
            restored_text, one_usage = self._restore_one(candidate.text)
            usage.add(one_usage)

            updated_text = (
                updated_text[:candidate.start_index]
                + restored_text
                + updated_text[candidate.end_index:]
            )

        return updated_text, usage

    def _restore_one(self, text: str) -> tuple[str, TokenUsage]:
        prompt = f"""
Restaura el siguiente texto jurídico con estas reglas:
1. NO cambies el sentido legal.
2. NO resumas.
3. NO elimines numeración, encabezados ni viñetas.
4. Corrige solo errores obvios de extracción/OCR:
   - palabras partidas por espacios
   - números de página incrustados
   - espacios erróneos dentro de palabras
5. Devuelve JSON: {{"restored_text": "..."}}.

TEXTO:
{text}
"""

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        output_text = getattr(response, "output_text", "") or ""
        usage = TokenUsage(
            input_tokens=getattr(getattr(response, "usage", None), "input_tokens", 0) or 0,
            output_tokens=getattr(getattr(response, "usage", None), "output_tokens", 0) or 0,
            total_tokens=getattr(getattr(response, "usage", None), "total_tokens", 0) or 0,
        )

        try:
            data = json.loads(output_text)
            restored = str(data.get("restored_text", "")).strip()
            return restored or text, usage
        except Exception:
            return text, usage