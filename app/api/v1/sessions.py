# app/api/v1/sessions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.deps import get_db
from app.schemas.sessions import SessionCreate, SessionOut
from app.schemas.orchestrator import OrchestratorMessageOut
from app.services.sessions_service import create_session, get_session, list_session_messages
from app.schemas.orchestrator_messages import OrchestratorMessageCreate, OrchestratorMessageOut
from app.services.orchestrator_messages_service import create_message

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut)
def create(payload: SessionCreate, db: Session = Depends(get_db)):
    try:
        s = create_session(db, user_id=payload.user_id)
        return SessionOut.model_validate(s)  # <- recomendado (ver schemas abajo)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/{session_id}", response_model=SessionOut)
def read(session_id: str, db: Session = Depends(get_db)):
    try:
        s = get_session(db, session_id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionOut.model_validate(s)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id (UUID expected)")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/{session_id}/messages", response_model=list[OrchestratorMessageOut])
def list_messages(session_id: str, db: Session = Depends(get_db)):
    try:
        s = get_session(db, session_id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")

        msgs = list_session_messages(db, session_id=session_id)
        return [OrchestratorMessageOut.model_validate(m) for m in msgs]
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id (UUID expected)")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")
    
#manual/qa
@router.post("/{session_id}/messages", response_model=OrchestratorMessageOut)
def add_message(session_id: str, payload: OrchestratorMessageCreate, db: Session = Depends(get_db)):
    try:
        msg = create_message(db, session_id=session_id, role=payload.role, content=payload.content)
        return OrchestratorMessageOut.model_validate(msg)

    except ValueError as e:
        if str(e) == "SESSION_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=400, detail="Bad request")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")