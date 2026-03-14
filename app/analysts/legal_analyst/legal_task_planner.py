from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set

from app.db.models.plan_step import PlanStep


@dataclass(frozen=True)
class LegalPlannedAction:
    key: str
    label: str
    status: str
    estimated_minutes: int


class LegalTaskPlanner:
    """
    Builds a legal analysis execution plan.

    This planner now supports two planning modes:
    1) from a high-level textual goal
    2) from assigned orchestrator plan_steps

    Canonical supported steps:
    - parse
    - segment
    - classify
    - detect_risk
    - detect_missing
    - explain
    - highlight
    - report
    """

    VALID_STEPS = {
        "parse",
        "segment",
        "classify",
        "detect_risk",
        "detect_missing",
        "explain",
        "highlight",
        "report",
    }

    BASE_STEPS = ["parse", "segment"]

    STEP_LABELS = {
        "parse": "Leer contrato",
        "segment": "Segmentar cláusulas",
        "classify": "Detectar estructura",
        "detect_risk": "Detectar riesgos",
        "detect_missing": "Detectar cláusulas faltantes",
        "explain": "Explicar cláusulas",
        "highlight": "Resaltar cláusulas",
        "report": "Generar informe final",
    }

    STEP_ESTIMATED_MINUTES = {
        "parse": 8,
        "segment": 16,
        "classify": 10,
        "detect_risk": 18,
        "detect_missing": 16,
        "explain": 12,
        "highlight": 10,
        "report": 12,
    }

    def create_plan(self, goal: str) -> List[str]:
        """
        Create an ordered execution plan from a user goal.
        """
        if not isinstance(goal, str):
            raise TypeError("goal must be a string")

        normalized_goal = goal.strip().lower()
        if not normalized_goal:
            return self.BASE_STEPS.copy()

        requested_steps: Set[str] = set(self.BASE_STEPS)

        if self._requires_classification(normalized_goal):
            requested_steps.add("classify")

        if self._contains_any(
            normalized_goal,
            {
                "risk",
                "risks",
                "critical",
                "critical clause",
                "critical clauses",
                "danger",
                "dangerous",
                "red flag",
                "red flags",
                "clausulas criticas",
                "riesgo",
                "riesgos",
            },
        ):
            requested_steps.add("classify")
            requested_steps.add("detect_risk")

        if self._contains_any(
            normalized_goal,
            {
                "missing",
                "missing clause",
                "missing clauses",
                "what is missing",
                "faltan",
                "faltante",
                "faltantes",
            },
        ):
            requested_steps.add("classify")
            requested_steps.add("detect_missing")

        if self._contains_any(
            normalized_goal,
            {
                "explain",
                "summary",
                "summarize",
                "executive summary",
                "executive",
                "resume",
                "resumen",
                "explica",
                "explicar",
            },
        ):
            requested_steps.add("classify")
            requested_steps.add("explain")

        if self._contains_any(
            normalized_goal,
            {
                "highlight",
                "mark",
                "underline",
                "subrayar",
                "resaltar",
                "highlight clauses",
            },
        ):
            requested_steps.add("classify")
            requested_steps.add("highlight")

        if self._contains_any(
            normalized_goal,
            {
                "report",
                "export",
                "exportable",
                "dashboard",
                "result",
                "results",
                "reporte",
                "exportar",
            },
        ):
            requested_steps.add("classify")
            requested_steps.add("report")

        if self._contains_any(
            normalized_goal,
            {
                "classify",
                "classification",
                "categorize",
                "category",
                "categorization",
                "tipo",
                "tipos",
                "categorizar",
                "clasificar",
            },
        ):
            requested_steps.add("classify")

        ordered_plan = self._order_steps(requested_steps)
        self._validate_plan(ordered_plan)
        return ordered_plan

    def create_plan_from_steps(self, plan_steps: Iterable[PlanStep | str]) -> List[str]:
        """
        Translate assigned orchestrator plan_steps into canonical legal analyst actions.
        """
        normalized_titles = self._normalize_step_titles(plan_steps)
        if not normalized_titles:
            return self.BASE_STEPS.copy()

        requested_steps: Set[str] = set()

        for title in normalized_titles:
            if self._contains_any(
                title,
                {
                    "recibir",
                    "archivo",
                    "documento",
                    "contrato",
                    "cargar",
                    "adjuntar",
                    "input",
                },
            ):
                requested_steps.add("parse")

            if self._contains_any(
                title,
                {
                    "analizar",
                    "análisis",
                    "analisis",
                    "contenido",
                    "estructura",
                    "clasificar",
                    "clasificación",
                    "clasificacion",
                    "tipo",
                    "categorizar",
                    "revisar documento",
                },
            ):
                requested_steps.add("classify")

            if self._contains_any(
                title,
                {
                    "segmentar",
                    "segmentación",
                    "segmentacion",
                    "cláusula",
                    "clausula",
                    "cláusulas",
                    "clausulas",
                    "listar cláusulas",
                    "listar clausulas",
                    "detectar cláusulas",
                    "detectar clausulas",
                },
            ):
                requested_steps.add("segment")

            if self._contains_any(
                title,
                {
                    "riesgo",
                    "riesgos",
                    "crítica",
                    "critica",
                    "críticas",
                    "criticas",
                    "red flag",
                    "red flags",
                },
            ):
                requested_steps.add("detect_risk")

            if self._contains_any(
                title,
                {
                    "faltante",
                    "faltantes",
                    "missing",
                    "omisión",
                    "omision",
                    "vacío",
                    "vacio",
                    "vacíos",
                    "vacios",
                },
            ):
                requested_steps.add("detect_missing")

            if self._contains_any(
                title,
                {
                    "explicar",
                    "explicación",
                    "explicacion",
                    "detallado",
                    "detalle",
                    "revisar informe",
                    "interpretar",
                    "explicar cláusulas",
                    "explicar clausulas",
                },
            ):
                requested_steps.add("explain")

            if self._contains_any(
                title,
                {
                    "resaltar",
                    "subrayar",
                    "marcar",
                    "highlight",
                },
            ):
                requested_steps.add("highlight")

            if self._contains_any(
                title,
                {
                    "informe",
                    "reporte",
                    "report",
                    "pdf",
                    "word",
                    "entregar",
                    "generar output",
                    "salida",
                    "entregable",
                    "formato pdf",
                    "formato word",
                },
            ):
                requested_steps.add("report")

        requested_steps = self._apply_dependencies(requested_steps)
        ordered_plan = self._order_steps(requested_steps)
        self._validate_plan(ordered_plan)
        return ordered_plan

    def create_action_objects_from_steps(
        self,
        plan_steps: Iterable[PlanStep | str],
    ) -> List[LegalPlannedAction]:
        ordered_plan = self.create_plan_from_steps(plan_steps)

        return [
            LegalPlannedAction(
                key=step_key,
                label=self.STEP_LABELS[step_key],
                status="pending",
                estimated_minutes=self.STEP_ESTIMATED_MINUTES[step_key],
            )
            for step_key in ordered_plan
        ]

    def _normalize_step_titles(self, plan_steps: Iterable[PlanStep | str]) -> List[str]:
        normalized: List[str] = []

        for item in plan_steps:
            if isinstance(item, str):
                title = item.strip().lower()
            else:
                title = str(getattr(item, "title", "") or "").strip().lower()

            if title:
                normalized.append(title)

        return normalized

    def _apply_dependencies(self, requested_steps: Set[str]) -> Set[str]:
        if "segment" in requested_steps:
            requested_steps.add("parse")

        if "classify" in requested_steps:
            requested_steps.add("parse")
            requested_steps.add("segment")

        if "detect_risk" in requested_steps:
            requested_steps.add("parse")
            requested_steps.add("segment")
            requested_steps.add("classify")

        if "detect_missing" in requested_steps:
            requested_steps.add("parse")
            requested_steps.add("segment")
            requested_steps.add("classify")

        if "explain" in requested_steps:
            requested_steps.add("parse")
            requested_steps.add("segment")
            requested_steps.add("classify")

        if "highlight" in requested_steps:
            requested_steps.add("parse")
            requested_steps.add("segment")
            requested_steps.add("classify")

        if "report" in requested_steps:
            requested_steps.add("parse")

        if not requested_steps:
            requested_steps.update(self.BASE_STEPS)

        return requested_steps

    def _requires_classification(self, goal: str) -> bool:
        return self._contains_any(
            goal,
            {
                "classify",
                "categorize",
                "category",
                "type",
                "risk",
                "critical",
                "missing",
                "summary",
                "explain",
                "highlight",
                "report",
                "clasificar",
                "categorizar",
                "tipo",
                "riesgo",
                "resumen",
                "explicar",
                "reporte",
                "subrayar",
                "resaltar",
            },
        )

    def _order_steps(self, requested_steps: Set[str]) -> List[str]:
        canonical_order = [
            "parse",
            "segment",
            "classify",
            "detect_risk",
            "detect_missing",
            "explain",
            "highlight",
            "report",
        ]
        return [step for step in canonical_order if step in requested_steps]

    def _validate_plan(self, plan: List[str]) -> None:
        if not isinstance(plan, list):
            raise TypeError("plan must be a list")

        invalid_steps = [step for step in plan if step not in self.VALID_STEPS]
        if invalid_steps:
            raise ValueError(f"Invalid plan steps detected: {invalid_steps}")

        if "segment" in plan and "parse" not in plan:
            raise ValueError("segment requires parse")

        if "classify" in plan and "segment" not in plan:
            raise ValueError("classify requires segment")

        if "detect_risk" in plan and "classify" not in plan:
            raise ValueError("detect_risk requires classify")

        if "detect_missing" in plan and "classify" not in plan:
            raise ValueError("detect_missing requires classify")

        if "explain" in plan and "classify" not in plan:
            raise ValueError("explain requires classify")

        if "highlight" in plan and "classify" not in plan:
            raise ValueError("highlight requires classify")

        if "report" in plan and "classify" not in plan:
            raise ValueError("report requires classify")

    def _contains_any(self, text: str, keywords: Set[str]) -> bool:
        return any(keyword in text for keyword in keywords)