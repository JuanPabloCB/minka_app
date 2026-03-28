# app/services/sessions_service.py
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models.orchestrator_session import OrchestratorSession
from app.db.models.orchestrator_message import OrchestratorMessage


def create_session(db: Session, user_id: str | None = None) -> OrchestratorSession:
    s = OrchestratorSession(user_id=user_id)  # status/created_at/updated_at por default
    db.add(s)

    try:
        db.commit()
        db.refresh(s)
        return s
    except Exception:
        db.rollback()
        raise

def get_session(db: Session, session_id: str) -> OrchestratorSession | None:
    return db.get(OrchestratorSession, uuid.UUID(session_id))


def list_session_messages(db: Session, session_id: str) -> list[OrchestratorMessage]:
    sid = uuid.UUID(session_id)
    stmt = (
        select(OrchestratorMessage)
        .where(OrchestratorMessage.session_id == sid)
        .order_by(OrchestratorMessage.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())