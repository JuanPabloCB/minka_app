# app/services/plans_service.py
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from app.db.models.orchestrator_session import OrchestratorSession
from app.db.models.plan import Plan
from app.db.models.plan_step import PlanStep

DEFAULT_STEPS = [
    "Confirmar objetivo exacto del usuario",
    "Verificar/solicitar archivos o data necesaria",
    "Preparar estructura y validaciones de datos",
    "Ejecutar análisis / transformación",
    "Generar output (archivo o respuesta) y registrar artefacto",
]

def create_draft_plan(db: Session, *, session_id: UUID, title: str) -> tuple[Plan, list[PlanStep]]:
    try:
        session = db.get(OrchestratorSession, session_id)
        if session is None:
            raise ValueError("SESSION_NOT_FOUND")
        if session.status == "closed":
            raise ValueError("SESSION_CLOSED")

        plan = Plan(session_id=session_id, status="draft", title=title or "")
        db.add(plan)
        db.flush()

        steps: list[PlanStep] = []
        for idx, step_title in enumerate(DEFAULT_STEPS, start=1):  # 👈 1..N (más natural)
            step = PlanStep(
                plan_id=plan.id,
                step_index=idx,
                title=step_title,
                status="pending",
            )
            db.add(step)
            steps.append(step)

        db.flush()
        db.commit()
        return plan, steps

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

def mark_plan_ready(db: Session, *, plan_id: UUID) -> Plan:
    try:
        plan = db.get(Plan, plan_id)
        if plan is None:
            raise ValueError("PLAN_NOT_FOUND")

        # anti-hallucination: solo draft → ready
        if plan.status != "draft":
            raise ValueError("PLAN_NOT_DRAFT")

        plan.status = "ready"
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan

    except Exception:
        db.rollback()
        raise