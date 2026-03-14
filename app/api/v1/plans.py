# app/api/v1/plans.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.plans import (
    PlanCreateDraftIn,
    PlanDraftOut,
    PlanOut,
    PlanReadyOut,
    PlanStepOut,
    PlanWithStepsOut,
    PlanListOut,
    PlanSetUIStateIn,
    PlanSetSelectedAnalystsIn,
    PlanMetaPatchIn,
    ExecutionRouteOut,
    ExecutionRouteStepOut,
    AnalystActionStepOut,
    SourceStepAssignmentOut,
)
from app.services.plans_service import (
    create_draft_plan,
    mark_plan_ready,
    get_plan_or_404,
    list_plan_steps,
    list_plans_by_session,
    set_plan_ui_state,
    set_plan_selected_analysts,
    merge_plan_meta,
)
from app.services.execution_route_service import get_execution_route

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/draft", response_model=PlanDraftOut)
def create_plan_draft(payload: PlanCreateDraftIn, db: Session = Depends(get_db)):
    """
    Crea (o reutiliza) un plan draft para una session.
    """
    try:
        result = create_draft_plan(db, session_id=payload.session_id, title=payload.title)

        return PlanDraftOut(
            plan=PlanOut.model_validate(result.plan),
            steps=[PlanStepOut.model_validate(s) for s in result.steps],
            created_new=result.created_new,
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
def set_ready(plan_id: UUID, db: Session = Depends(get_db)):
    """
    draft -> ready (y ui_state=ready)
    """
    try:
        plan = mark_plan_ready(db, plan_id=plan_id)
        return PlanReadyOut(plan_id=plan.id, status=plan.status, ui_state=plan.ui_state)

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
    Devuelve plan + steps (aunque en UI no los muestres, quedan disponibles).
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
    

@router.get("/{plan_id}/execution-route", response_model=ExecutionRouteOut)
def read_execution_route(plan_id: UUID, db: Session = Depends(get_db)):
    """
    Devuelve la ruta de ejecución derivada desde plan + plan_steps.
    V1:
    - todos los steps se asignan a legal_analyst
    - los consecutivos del mismo analista se agrupan
    - no ejecuta analistas reales todavía
    """
    try:
        result = get_execution_route(db, plan_id=plan_id)

        return ExecutionRouteOut(
            plan=PlanOut.model_validate(result.plan),
            progress_percent=result.progress_percent,
            execution_status=result.execution_status,
            estimated_total_minutes=result.estimated_total_minutes,
            execution_steps=[
                ExecutionRouteStepOut(
                    index=step.index,
                    analyst_key=step.analyst_key,
                    analyst_label=step.analyst_label,
                    status=step.status,
                    estimated_minutes=step.estimated_minutes,
                    task_titles=step.task_titles,
                    source_step_indexes=step.source_step_indexes,
                    source_step_assignments=[
                        SourceStepAssignmentOut(
                            step_index=assignment.step_index,
                            title=assignment.title,
                            analyst_key=assignment.analyst_key,
                            analyst_label=assignment.analyst_label,
                        )
                        for assignment in step.source_step_assignments
                    ],
                    analyst_actions=[
                        AnalystActionStepOut(
                            key=action.key,
                            label=action.label,
                            status=action.status,
                            estimated_minutes=action.estimated_minutes,
                        )
                        for action in step.analyst_actions
                    ],
                    expected_output=step.expected_output,
                )
                for step in result.execution_steps
            ],
        )

    except ValueError as e:
        if str(e) == "PLAN_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Plan not found")
        raise HTTPException(status_code=400, detail="Bad request")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/{plan_id}/steps", response_model=list[PlanStepOut])
def read_steps(plan_id: UUID, db: Session = Depends(get_db)):
    try:
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
    try:
        plans = list_plans_by_session(db, session_id=session_id)
        return PlanListOut(plans=[PlanOut.model_validate(p) for p in plans])
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


# --- Endpoints PRO para tu UI de Analistas ---

@router.post("/{plan_id}/ui-state", response_model=PlanOut)
def update_ui_state(plan_id: UUID, payload: PlanSetUIStateIn, db: Session = Depends(get_db)):
    try:
        plan = set_plan_ui_state(db, plan_id=plan_id, ui_state=payload.ui_state)
        return PlanOut.model_validate(plan)
    except ValueError as e:
        if str(e) == "PLAN_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Plan not found")
        raise HTTPException(status_code=400, detail="Bad request")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.post("/{plan_id}/selected-analysts", response_model=PlanOut)
def update_selected_analysts(
    plan_id: UUID, payload: PlanSetSelectedAnalystsIn, db: Session = Depends(get_db)
):
    try:
        plan = set_plan_selected_analysts(
            db, plan_id=plan_id, selected_analysts=payload.selected_analysts
        )
        return PlanOut.model_validate(plan)
    except ValueError as e:
        if str(e) == "PLAN_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Plan not found")
        raise HTTPException(status_code=400, detail="Bad request")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.post("/{plan_id}/meta", response_model=PlanOut)
def patch_meta(plan_id: UUID, payload: PlanMetaPatchIn, db: Session = Depends(get_db)):
    try:
        plan = merge_plan_meta(db, plan_id=plan_id, patch=payload.patch)
        return PlanOut.model_validate(plan)
    except ValueError as e:
        if str(e) == "PLAN_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Plan not found")
        raise HTTPException(status_code=400, detail="Bad request")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")