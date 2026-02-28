# app/api/v1/orchestrator.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.deps import get_db
from app.schemas.orchestrator import OrchestratorMessageIn, OrchestratorMessageOut
from app.services.orchestrator_service import create_user_and_assistant_messages

from app.schemas.orchestrator_turn import OrchestratorTurnIn, OrchestratorTurnOut
from app.services.orchestrator_turn_service import orchestrator_turn

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.post("/message", response_model=OrchestratorMessageOut)
def post_message(payload: OrchestratorMessageIn, db: Session = Depends(get_db)):
    try:
        result = orchestrator_turn(db, session_id=payload.session_id, user_text=payload.content)

        return OrchestratorMessageOut(
            session_id=payload.session_id,
            user_message_id=result["user_msg"].id,
            assistant_message_id=result["assistant_msg"].id,
            reply=result["reply"],
            created_at=result["assistant_msg"].created_at,
            ui_hints=result.get("ui_hints"),
        )

    except ValueError as e:
        if str(e) == "SESSION_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        raise HTTPException(status_code=400, detail="Bad request")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")
    

@router.post("/turn/{session_id}", response_model=OrchestratorTurnOut)
def turn(session_id: UUID, payload: OrchestratorTurnIn, db: Session = Depends(get_db)):
    try:
        result = orchestrator_turn(db, session_id=session_id, user_text=payload.content)

        return OrchestratorTurnOut(
            session_id=session_id,
            user_message_id=result["user_msg"].id,
            assistant_message_id=result["assistant_msg"].id,
            reply=result["reply"],
            created_at=result["assistant_msg"].created_at,
            cta_ready=result["cta_ready"],
            plan_created=result["plan_created"],
            plan_id=result["plan_id"],
            plan_status=result["plan_status"],
            ui_hints=result.get("ui_hints"),
        )

    except ValueError as e:
        if str(e) == "SESSION_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=400, detail="Bad request")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")
