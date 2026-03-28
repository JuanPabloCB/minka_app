from __future__ import annotations

import re

from .candidate_builder import CandidateBuilder
from .formatter import FindingsFormatter
from .llm_verifier import LLMClauseVerifier
from .parser import ClauseParser
from .partitioner import ClausePartitioner
from .tree_validator import ClauseTreeValidator
from .types import ClauseDetectionResult, ContractUnit, DocumentLayout, TokenUsage


class LegalAnalystFindingsPipelineV2:
    """
    Versión vendible:
    - confirma solo cláusulas madre con encabezado real explícito
    - NO recupera cláusulas madre por gaps
    - NO crea cláusulas madre sintéticas por jerarquía
    - usa LLM solo para afinar hijos ambiguos
    - soporta modo texto y modo layout
    - prioriza mantener cláusulas madre + subcláusulas + list items
      sin contaminarse con anexos/tablas del appendix
    """

    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.parser = ClauseParser()
        self.builder = CandidateBuilder(parser=self.parser)
        self.partitioner = ClausePartitioner(parser=self.parser)
        self.verifier = LLMClauseVerifier(model=model)
        self.validator = ClauseTreeValidator()
        self.formatter = FindingsFormatter()

    def _find_missing_main_clause_ranks(
        self,
        formal_clauses: list[ContractUnit],
    ) -> list[int]:
        ranks = sorted(
            {int(c.ordinal_rank) for c in formal_clauses if c.ordinal_rank is not None}
        )
        if not ranks:
            return []

        missing: list[int] = []

        for idx in range(len(ranks) - 1):
            current_rank = ranks[idx]
            next_rank = ranks[idx + 1]
            if next_rank - current_rank > 1:
                missing.extend(range(current_rank + 1, next_rank))

        return sorted(set(missing))

    def _run_core(
        self,
        contract_units: dict[str, list[ContractUnit]],
        full_text_for_verifier: str,
        appendix_text: str,
    ) -> ClauseDetectionResult:
        partition = self.partitioner.partition_units_for_clause_detection(contract_units)

        usage = TokenUsage()

        llm_verdicts = []
        accepted_llm_units: list[ContractUnit] = []
        needs_review_units: list[ContractUnit] = []

        llm_candidates = [
            u for u in partition.llm_candidates
            if u.level in {"subclause", "list_item"}
        ]

        if llm_candidates:
            llm_verdicts, usage_ambiguous = self.verifier.verify_units(
                units=llm_candidates,
                formal_clauses=contract_units.get("formal_clauses", []),
                full_text=full_text_for_verifier,
            )
            usage.add(usage_ambiguous)

            accepted_llm_units, needs_review_units = self.verifier.apply_verdicts_to_candidates(
                possible_units=llm_candidates,
                verdicts=llm_verdicts,
            )

        merged_units = partition.trusted_units + accepted_llm_units
        validated_units = self.validator.validate(merged_units)

        confirmed_main_clauses = list(validated_units.get("formal_clauses", []))
        missing_expected_ranks = self._find_missing_main_clause_ranks(confirmed_main_clauses)

        final_validated_units = dict(validated_units)
        final_validated_units["formal_clauses"] = confirmed_main_clauses

        return self.formatter.format_result(
            validated_units=final_validated_units,
            appendix_text=appendix_text,
            token_usage=usage,
            possible_main_clauses=[],
            missing_expected_ranks=missing_expected_ranks,
        )

    def run_all_clauses(self, extracted_text: str) -> ClauseDetectionResult:
        """
        Flujo basado en texto plano.
        """
        cleaned = self.parser.clean_extracted_text(extracted_text)
        main_body_text, appendix_text = self.parser.split_main_body_and_appendices(cleaned)

        contract_units = self.builder.build_contract_units(main_body_text)

        return self._run_core(
            contract_units=contract_units,
            full_text_for_verifier=main_body_text,
            appendix_text=appendix_text,
        )

    def _crop_layout_to_main_body(
        self,
        layout: DocumentLayout,
        main_body_text: str,
    ) -> DocumentLayout:
        """
        Recorta el layout a solo el cuerpo principal del contrato.
        Esto evita que anexos, tablas, diagramas y normas técnicas del appendix
        entren como supuestas cláusulas o subcláusulas.
        """
        if not layout or not main_body_text:
            return layout

        cutoff = len(main_body_text)
        if cutoff <= 0:
            return layout

        kept_lines = [
            line for line in layout.lines
            if int(getattr(line, "global_start", 0)) < cutoff
        ]

        return DocumentLayout(
            full_text=main_body_text,
            lines=kept_lines,
            page_count=layout.page_count,
        )

    def run_all_clauses_from_layout(self, layout: DocumentLayout) -> ClauseDetectionResult:
        """
        Flujo basado en layout real del PDF.
        Importante: recorta el layout al cuerpo principal antes de construir unidades.
        """
        raw_full_text = layout.full_text or ""
        main_body_text, appendix_text = self.parser.split_main_body_and_appendices(raw_full_text)

        cropped_layout = self._crop_layout_to_main_body(
            layout=layout,
            main_body_text=main_body_text,
        )

        contract_units = self.builder.build_contract_units_from_layout(cropped_layout)

        return self._run_core(
            contract_units=contract_units,
            full_text_for_verifier=main_body_text,
            appendix_text=appendix_text,
        )

    def _get_item_value(self, item, *keys):
        if item is None:
            return None

        if isinstance(item, dict):
            for key in keys:
                if key in item and item.get(key) is not None:
                    return item.get(key)
            return None

        for key in keys:
            value = getattr(item, key, None)
            if value is not None:
                return value

        return None

    def _normalize_title(self, title: str | None) -> str:
        return re.sub(r"\s+", " ", (title or "").strip())

    def _looks_like_explicit_contract_header(self, title: str | None) -> bool:
        clean = self._normalize_title(title).lower()
        return bool(
            re.match(
                r"^(cl[áa]usula|art[íi]culo|secci[óo]n)\b",
                clean,
                flags=re.IGNORECASE,
            )
        )

    def _looks_like_noisy_main_title(self, title: str | None) -> bool:
        clean = self._normalize_title(title)
        if not clean:
            return True

        if self._looks_like_explicit_contract_header(clean):
            return False

        alpha_count = sum(1 for c in clean if c.isalpha())
        digit_count = sum(1 for c in clean if c.isdigit())

        if alpha_count == 0:
            return True

        if digit_count > alpha_count:
            return True

        if re.match(r"^\d+(?:\.\d+)?\s*$", clean):
            return True

        if re.match(r"^\d+(?:\.\d+)?\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ]+$", clean):
            # esto puede ser sección técnica; no lo marcamos de frente como ruido
            return False

        # títulos muy tabulares / gráficos / medidas
        noisy_patterns = [
            r"\(aprox\)",
            r"[½¾]",
            r"\b\d+\s+\d+\s+\d+\b",
            r"^\d+\s+\([^)]+\)\s+\d+",
            r"^[\d\s\-\./º°]+$",
        ]
        for pattern in noisy_patterns:
            if re.search(pattern, clean, flags=re.IGNORECASE):
                return True

        if len(clean) <= 4:
            return True

        return False

    def _count_explicit_main_headers(self, result: ClauseDetectionResult) -> int:
        items = list(result.formal_clauses or [])
        count = 0

        for item in items:
            title = self._get_item_value(item, "title_guess", "title")
            if self._looks_like_explicit_contract_header(title):
                count += 1

        return count

    def _count_noisy_main_headers(self, result: ClauseDetectionResult) -> int:
        items = list(result.formal_clauses or [])
        count = 0

        for item in items:
            title = self._get_item_value(item, "title_guess", "title")
            if self._looks_like_noisy_main_title(title):
                count += 1

        return count

    def _score_result(self, result: ClauseDetectionResult) -> tuple[int, int, int, int, int]:
        """
        Score para elegir el mejor resultado entre texto vs layout.
        Prioridad real:
        1. más encabezados contractuales explícitos (CLÁUSULA / ARTÍCULO / SECCIÓN)
        2. menos encabezados basura
        3. más cláusulas formales válidas
        4. menos faltantes
        5. más estructura hija, pero con bono capado para que el ruido no gane por volumen
        """
        formal_count = len(result.formal_clauses or [])
        missing_count = len(result.missing_expected_ranks or [])
        child_count = len(result.subclauses or []) + len(result.list_items or [])

        explicit_main_count = self._count_explicit_main_headers(result)
        noisy_main_count = self._count_noisy_main_headers(result)

        child_bonus = min(child_count, 80)

        return (
            explicit_main_count,
            -noisy_main_count,
            formal_count,
            -missing_count,
            child_bonus,
        )

    def run_best_effort(
        self,
        extracted_text: str,
        layout: DocumentLayout | None = None,
    ) -> ClauseDetectionResult:
        """
        Ejecuta texto plano siempre.
        Si hay layout, ejecuta ambos y elige el mejor.
        """
        text_result = self.run_all_clauses(extracted_text)

        if layout is None:
            return text_result

        layout_result = self.run_all_clauses_from_layout(layout)

        text_score = self._score_result(text_result)
        layout_score = self._score_result(layout_result)

        print("===== RESULT SCORE DEBUG =====")
        print("TEXT SCORE:", text_score)
        print("LAYOUT SCORE:", layout_score)
        print("TEXT formal:", len(text_result.formal_clauses or []))
        print("LAYOUT formal:", len(layout_result.formal_clauses or []))
        print("TEXT sub+list:", len(text_result.subclauses or []) + len(text_result.list_items or []))
        print("LAYOUT sub+list:", len(layout_result.subclauses or []) + len(layout_result.list_items or []))
        print("================================")

        if layout_score > text_score:
            print("WINNER: LAYOUT")
            return layout_result

        print("WINNER: TEXT")
        return text_result