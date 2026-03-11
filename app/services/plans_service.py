# app/services/plans_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.orchestrator_session import OrchestratorSession
from app.db.models.plan import Plan
from app.db.models.plan_step import PlanStep


DEFAULT_STEPS: list[str] = [
    "Confirmar objetivo exacto del usuario",
    "Verificar/solicitar archivos o data necesaria",
    "Definir validaciones y criterios de salida",
    "Ejecutar procesamiento/acción con analista",
    "Generar output y registrar artefacto",
]


@dataclass(frozen=True)
class PlanCreateResult:
    plan: Plan
    steps: list[PlanStep]
    created_new: bool  # True si creamos uno nuevo, False si reutilizamos draft existente


def _get_open_session_or_raise(db: Session, session_id: UUID) -> OrchestratorSession:
    session = db.get(OrchestratorSession, session_id)
    if session is None:
        raise ValueError("SESSION_NOT_FOUND")
    if getattr(session, "status", None) == "closed":
        raise ValueError("SESSION_CLOSED")
    return session


def _get_latest_draft_plan(db: Session, session_id: UUID) -> Plan | None:
    stmt = (
        select(Plan)
        .where(Plan.session_id == session_id)
        .where(Plan.status == "draft")
        .order_by(Plan.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _ensure_plan_steps(db: Session, *, plan: Plan, step_titles: Iterable[str]) -> list[PlanStep]:
    steps: list[PlanStep] = []
    for idx, step_title in enumerate(step_titles, start=1):
        step = PlanStep(
            plan_id=plan.id,
            step_index=idx,
            title=str(step_title).strip(),
            status="pending",
        )
        db.add(step)
        steps.append(step)
    db.flush()
    return steps


def create_draft_plan(
    db: Session,
    *,
    session_id: UUID,
    title: str,
    steps_titles: list[str] | None = None,
    reuse_existing_draft: bool = True,
) -> PlanCreateResult:
    """
    Crea un Plan en estado draft + sus PlanSteps.

    - reuse_existing_draft=True: si ya existe un draft para esa session, lo reutiliza (idempotente).
    - steps_titles: si viene vacío/None, usa DEFAULT_STEPS.
    """
    _get_open_session_or_raise(db, session_id)

    if reuse_existing_draft:
        existing = _get_latest_draft_plan(db, session_id)
        if existing is not None:
            existing_steps = list_plan_steps(db, plan_id=existing.id)
            if not existing_steps:
                steps = _ensure_plan_steps(
                    db, plan=existing, step_titles=steps_titles or DEFAULT_STEPS
                )
                db.commit()
                db.refresh(existing)
                return PlanCreateResult(plan=existing, steps=steps, created_new=False)

            return PlanCreateResult(plan=existing, steps=existing_steps, created_new=False)

    step_titles = steps_titles or DEFAULT_STEPS
    step_titles = [s.strip() for s in step_titles if str(s).strip()] or DEFAULT_STEPS

    try:
        plan = Plan(
            session_id=session_id,
            status="draft",
            title=(title or "").strip(),
            ui_state="configuring",
            # Estos defaults normalmente ya existen en tu modelo, pero lo dejamos explícito:
            selected_analysts=[],
            meta={},
        )
        db.add(plan)
        db.flush()

        steps = _ensure_plan_steps(db, plan=plan, step_titles=step_titles)

        db.commit()
        db.refresh(plan)
        return PlanCreateResult(plan=plan, steps=steps, created_new=True)

    except Exception:
        db.rollback()
        raise


def get_plan(db: Session, *, plan_id: UUID) -> Plan | None:
    return db.get(Plan, plan_id)


def get_plan_or_404(db: Session, *, plan_id: UUID) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise ValueError("PLAN_NOT_FOUND")
    return plan


def list_plan_steps(db: Session, *, plan_id: UUID) -> list[PlanStep]:
    stmt = (
        select(PlanStep)
        .where(PlanStep.plan_id == plan_id)
        .order_by(PlanStep.step_index.asc())
    )
    return list(db.execute(stmt).scalars().all())


def list_plans_by_session(db: Session, *, session_id: UUID) -> list[Plan]:
    stmt = (
        select(Plan)
        .where(Plan.session_id == session_id)
        .order_by(Plan.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def set_plan_ui_state(db: Session, *, plan_id: UUID, ui_state: str) -> Plan:
    try:
        plan = get_plan_or_404(db, plan_id=plan_id)
        plan.ui_state = (ui_state or "").strip() or "configuring"
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan
    except Exception:
        db.rollback()
        raise


def set_plan_selected_analysts(db: Session, *, plan_id: UUID, selected_analysts: list[dict]) -> Plan:
    try:
        plan = get_plan_or_404(db, plan_id=plan_id)
        plan.selected_analysts = selected_analysts or []
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan
    except Exception:
        db.rollback()
        raise


def merge_plan_meta(db: Session, *, plan_id: UUID, patch: dict) -> Plan:
    """
    Hace merge superficial (shallow) del dict meta.
    """
    try:
        plan = get_plan_or_404(db, plan_id=plan_id)
        current = plan.meta or {}
        if not isinstance(current, dict):
            current = {}
        if patch and isinstance(patch, dict):
            current.update(patch)
        plan.meta = current
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan
    except Exception:
        db.rollback()
        raise


def mark_plan_ready(db: Session, *, plan_id: UUID) -> Plan:
    """
    draft -> ready
    Además, setea ui_state="ready" para tu pantalla "Listo".
    """
    try:
        plan = get_plan_or_404(db, plan_id=plan_id)

        if plan.status != "draft":
            raise ValueError("PLAN_NOT_DRAFT")

        plan.status = "ready"
        plan.ui_state = "ready"

        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan

    except Exception:
        db.rollback()
        raise