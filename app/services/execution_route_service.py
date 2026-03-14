from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.plan import Plan
from app.db.models.plan_step import PlanStep
from app.services.plans_service import get_plan_or_404, list_plan_steps
from app.services.analyst_assignment_service import assign_analyst_to_step
from app.analysts.legal_analyst.legal_task_planner import LegalTaskPlanner, LegalPlannedAction


@dataclass(frozen=True)
class ExecutionRouteStep:
    index: int
    analyst_key: str
    analyst_label: str
    status: str
    estimated_minutes: int
    task_titles: list[str]
    source_step_indexes: list[int]
    source_step_assignments: list[SourceStepAssignment]
    analyst_actions: list[LegalPlannedAction]
    expected_output: str


@dataclass(frozen=True)
class ExecutionRouteResult:
    plan: Plan
    progress_percent: int
    execution_status: str
    estimated_total_minutes: int
    execution_steps: list[ExecutionRouteStep]


@dataclass(frozen=True)
class SourceStepAssignment:
    step_index: int
    title: str
    analyst_key: str
    analyst_label: str

@dataclass(frozen=True)
class EnrichedPlanStep:
    source_step: PlanStep
    title: str
    analyst_key: str
    analyst_label: str
    estimated_minutes: int

def get_execution_route(db: Session, *, plan_id: UUID) -> ExecutionRouteResult:
    plan = get_plan_or_404(db, plan_id=plan_id)
    steps = list_plan_steps(db, plan_id=plan_id)

    if not steps:
        return ExecutionRouteResult(
            plan=plan,
            progress_percent=0,
            execution_status="Esperando",
            estimated_total_minutes=0,
            execution_steps=[],
        )

    enriched = [_to_enriched_plan_step(step) for step in steps]
    grouped = _group_consecutive_steps(enriched)

    execution_steps: list[ExecutionRouteStep] = []
    for idx, group in enumerate(grouped, start=1):
        source_steps = [item.source_step for item in group]
        task_titles = [item.title for item in group]
        source_step_indexes = [item.source_step.step_index for item in group]

        analyst_key = group[0].analyst_key
        analyst_label = group[0].analyst_label

        source_step_assignments = [
            SourceStepAssignment(
                step_index=item.source_step.step_index,
                title=item.title,
                analyst_key=item.analyst_key,
                analyst_label=item.analyst_label,
            )
            for item in group
        ]

        analyst_actions = _translate_steps_with_analyst(
            analyst_key=analyst_key,
            plan_steps=source_steps,
        )

        estimated_minutes = sum(action.estimated_minutes for action in analyst_actions)
        if estimated_minutes <= 0:
            estimated_minutes = sum(item.estimated_minutes for item in group)

        execution_steps.append(
            ExecutionRouteStep(
                index=idx,
                analyst_key=analyst_key,
                analyst_label=analyst_label,
                status="pending",
                estimated_minutes=estimated_minutes,
                task_titles=task_titles,
                source_step_indexes=source_step_indexes,
                source_step_assignments=source_step_assignments,
                analyst_actions=analyst_actions,
                expected_output=_infer_expected_output(group),
            )
        )

    estimated_total_minutes = sum(step.estimated_minutes for step in execution_steps)

    return ExecutionRouteResult(
        plan=plan,
        progress_percent=_compute_progress_percent(steps=steps),
        execution_status=_compute_execution_status(plan=plan, steps=steps),
        estimated_total_minutes=estimated_total_minutes,
        execution_steps=execution_steps,
    )


def _to_enriched_plan_step(step: PlanStep) -> EnrichedPlanStep:
    title = (step.title or "").strip()

    assignment = assign_analyst_to_step(step)
    analyst_key = assignment.analyst_key
    analyst_label = _get_analyst_label(analyst_key)

    return EnrichedPlanStep(
        source_step=step,
        title=title,
        analyst_key=analyst_key,
        analyst_label=analyst_label,
        estimated_minutes=_estimate_step_minutes(title),
    )


def _translate_steps_with_analyst(
    *,
    analyst_key: str,
    plan_steps: list[PlanStep],
) -> list[LegalPlannedAction]:
    if analyst_key == "legal_analyst":
        planner = LegalTaskPlanner()
        return planner.create_action_objects_from_steps(plan_steps)

    return []


def _get_analyst_label(analyst_key: str) -> str:
    if analyst_key == "legal_analyst":
        return "Analyst Legal"
    if analyst_key == "reporting_analyst":
        return "Analyst Reporting"
    return "Analyst"


def _group_consecutive_steps(steps: list[EnrichedPlanStep]) -> list[list[EnrichedPlanStep]]:
    if not steps:
        return []

    groups: list[list[EnrichedPlanStep]] = []
    current_group: list[EnrichedPlanStep] = [steps[0]]

    for step in steps[1:]:
        if step.analyst_key == current_group[-1].analyst_key:
            current_group.append(step)
        else:
            groups.append(current_group)
            current_group = [step]

    groups.append(current_group)
    return groups


def _estimate_step_minutes(title: str) -> int:
    normalized = (title or "").strip().lower()

    if _contains_any(
        normalized,
        {
            "confirmar",
            "objetivo",
            "meta",
            "verificar",
            "solicitar",
            "archivo",
            "data",
            "información",
            "informacion",
            "validaciones",
            "criterios",
            "entrada",
            "input",
        },
    ):
        return 8

    if _contains_any(
        normalized,
        {
            "cláusula",
            "clausula",
            "cláusulas",
            "clausulas",
            "riesgo",
            "riesgos",
            "crítica",
            "critica",
            "críticas",
            "criticas",
            "contrato",
            "analizar",
            "análisis",
            "analisis",
            "detectar",
            "revisar",
            "clasificar",
            "segmentar",
        },
    ):
        return 16

    if _contains_any(
        normalized,
        {
            "generar",
            "output",
            "salida",
            "registrar",
            "artefacto",
            "reporte",
            "report",
            "resumen",
            "documento",
            "entregable",
        },
    ):
        return 11

    return 10


def _infer_expected_output(group: list[EnrichedPlanStep]) -> str:
    joined_titles = " ".join((item.title or "").strip().lower() for item in group)

    if _contains_any(
        joined_titles,
        {
            "riesgo",
            "riesgos",
            "crítica",
            "critica",
            "críticas",
            "criticas",
            "cláusula",
            "clausula",
            "cláusulas",
            "clausulas",
        },
    ):
        return "Análisis legal inicial"

    if _contains_any(
        joined_titles,
        {
            "reporte",
            "report",
            "resumen",
            "output",
            "salida",
            "artefacto",
            "documento",
        },
    ):
        return "Entregable generado"

    return "Resultado intermedio"


def _compute_progress_percent(*, steps: list[PlanStep]) -> int:
    if not steps:
        return 0

    done_count = sum(1 for step in steps if (step.status or "").strip().lower() == "done")
    return int((done_count / len(steps)) * 100)


def _compute_execution_status(*, plan: Plan, steps: list[PlanStep]) -> str:
    plan_status = (plan.status or "").strip().lower()

    if plan_status == "error" or any((step.status or "").strip().lower() == "error" for step in steps):
        return "Error"

    if steps and all((step.status or "").strip().lower() == "done" for step in steps):
        return "Completado"

    if any((step.status or "").strip().lower() == "running" for step in steps):
        return "En proceso"

    return "Esperando"


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)