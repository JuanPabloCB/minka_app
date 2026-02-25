# app/api/v1/plans.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.deps import get_db
from app.schemas.plans import (
    PlanCreateDraftIn,
    PlanDraftOut,
    PlanOut,
    PlanReadyOut,
    PlanStepOut,
    PlanWithStepsOut,
    PlanListOut,
)
from app.services.plans_service import (
    create_draft_plan,
    mark_plan_ready,
    get_plan_or_404,
    list_plan_steps,
    list_plans_by_session,
)

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/draft", response_model=PlanDraftOut)
def create_plan_draft(payload: PlanCreateDraftIn, db: Session = Depends(get_db)):
    try:
        plan, steps = create_draft_plan(db, session_id=payload.session_id, title=payload.title)

        return PlanDraftOut(
            plan=PlanOut.model_validate(plan),
            steps=[PlanStepOut.model_validate(s) for s in steps],
        )

    except ValueError as e:
        if str(e) == "SESSION_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Session not found")
        if str(e) == "SESSION_CLOSED":
            raise HTTPException(status_code=409, detail="Session is closed")
        raise HTTPException(status_code=400, detail="Bad request")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.post("/{plan_id}/ready", response_model=PlanReadyOut)
def set_plan_ready(plan_id: UUID, db: Session = Depends(get_db)):
    try:
        plan = mark_plan_ready(db, plan_id=plan_id)
        return PlanReadyOut(plan_id=plan.id, status=plan.status)

    except ValueError as e:
        if str(e) == "PLAN_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Plan not found")
        if str(e) == "PLAN_NOT_DRAFT":
            raise HTTPException(status_code=409, detail="Plan must be in draft to mark ready")
        raise HTTPException(status_code=400, detail="Bad request")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/{plan_id}", response_model=PlanWithStepsOut)
def read_plan(plan_id: UUID, db: Session = Depends(get_db)):
    """
    Devuelve plan + steps.
    """
    try:
        plan = get_plan_or_404(db, plan_id=plan_id)
        steps = list_plan_steps(db, plan_id=plan_id)

        return PlanWithStepsOut(
            plan=PlanOut.model_validate(plan),
            steps=[PlanStepOut.model_validate(s) for s in steps],
        )

    except ValueError as e:
        if str(e) == "PLAN_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Plan not found")
        raise HTTPException(status_code=400, detail="Bad request")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/{plan_id}/steps", response_model=list[PlanStepOut])
def read_plan_steps(plan_id: UUID, db: Session = Depends(get_db)):
    """
    Devuelve solo steps del plan.
    """
    try:
        # valida que plan exista
        _ = get_plan_or_404(db, plan_id=plan_id)

        steps = list_plan_steps(db, plan_id=plan_id)
        return [PlanStepOut.model_validate(s) for s in steps]

    except ValueError as e:
        if str(e) == "PLAN_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Plan not found")
        raise HTTPException(status_code=400, detail="Bad request")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/by-session/{session_id}", response_model=PlanListOut)
def list_plans(session_id: UUID, db: Session = Depends(get_db)):
    """
    Lista planes de una sesión (útil para UI).
    """
    try:
        plans = list_plans_by_session(db, session_id=session_id)
        return PlanListOut(plans=[PlanOut.model_validate(p) for p in plans])

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")