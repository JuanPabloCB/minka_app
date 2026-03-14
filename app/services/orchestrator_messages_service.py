from sqlalchemy.orm import Session

from app.db.models.orchestrator_session import OrchestratorSession
from app.db.models.orchestrator_message import OrchestratorMessage


def create_message(db: Session, session_id, role: str, content: str, meta: dict | None = None):
    s = db.query(OrchestratorSession).filter(OrchestratorSession.id == session_id).first()
    if not s:
        raise ValueError("SESSION_NOT_FOUND")

    msg = OrchestratorMessage(
        session_id=session_id,
        role=role,
        content=content,
        meta=meta or {},
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg