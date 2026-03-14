from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.db.models.plan_step import PlanStep


@dataclass(frozen=True)
class AnalystAssignment:
    step_index: int
    analyst_key: str
    reason: str


AVAILABLE_ANALYST_KEYS = {
    "legal_analyst",
    # "reporting_analyst",  # se activará cuando exista de verdad
}


def assign_analyst_to_step(step: PlanStep) -> AnalystAssignment:
    """
    Decide qué analista debe encargarse de un plan_step.

    V1:
    - Solo existe legal_analyst
    - Por diseño devolvemos legal_analyst para todo
    - Dejamos la interfaz lista para futura lógica real multi-analista
    """
    step_index = int(getattr(step, "step_index", 0) or 0)

    return AnalystAssignment(
        step_index=step_index,
        analyst_key="legal_analyst",
        reason="Default analyst assignment: only legal_analyst is currently available.",
    )


def assign_analysts_to_steps(steps: Iterable[PlanStep]) -> list[AnalystAssignment]:
    return [assign_analyst_to_step(step) for step in steps]