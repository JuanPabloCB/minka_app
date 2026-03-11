from __future__ import annotations

from typing import List, Set


class LegalTaskPlanner:
    """
    Builds a legal analysis execution plan based on the user's goal.

    The planner is intentionally simple, deterministic, and transparent.
    It translates a user goal into an ordered list of execution steps.

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

    def create_plan(self, goal: str) -> List[str]:
        """
        Create an ordered execution plan from a user goal.

        Rules:
        - parse and segment are always required
        - classify is required for nearly all analytical tasks
        - detect_risk is added for risk / critical clause review
        - detect_missing is added for missing clause review
        - explain is added for summaries / explanations / executive understanding
        - highlight is added for marking or underlining clauses
        - report is added for exportable or summarized outputs
        """
        if not isinstance(goal, str):
            raise TypeError("goal must be a string")

        normalized_goal = goal.strip().lower()
        if not normalized_goal:
            return self.BASE_STEPS.copy()

        requested_steps: Set[str] = set(self.BASE_STEPS)

        # Classification is the backbone of most downstream legal tasks.
        if self._requires_classification(normalized_goal):
            requested_steps.add("classify")

        # Risk / critical review
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

        # Missing clauses
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

        # Explanation / summary
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

        # Highlighting / marking / underlining
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

        # Reporting / output-oriented requests
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

        # If the user asks for classification/categorization directly
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

        # Ensure dependencies
        ordered_plan = self._order_steps(requested_steps)

        self._validate_plan(ordered_plan)

        return ordered_plan

    def _requires_classification(self, goal: str) -> bool:
        """
        Classification is required in most useful legal analysis goals.
        """
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
        """
        Return the canonical order of execution.
        """
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
        """
        Validate plan integrity and dependencies.
        """
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