# app/services/orchestrator_service.py
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.models.orchestrator_session import OrchestratorSession
from app.db.models.orchestrator_message import OrchestratorMessage


def _mock_reply(user_text: str) -> str:
    return (
        "Entendido. Puedo crear un plan para lograr eso. "
        "¿Qué archivo/datos usarás (Excel/CSV) y qué columnas claves tiene?"
    )


def create_user_and_assistant_messages(
    db: Session, *, session_id: UUID, user_text: str
) -> OrchestratorMessage:
    try:
        session = db.get(OrchestratorSession, session_id)
        if session is None:
            raise ValueError("SESSION_NOT_FOUND")

        # (opcional pero recomendado)
        if session.status == "closed":
            raise ValueError("SESSION_CLOSED")

        user_msg = OrchestratorMessage(
            session_id=session_id,
            role="user",
            content=user_text,
        )
        db.add(user_msg)
        db.flush()

        reply = _mock_reply(user_text)
        assistant_msg = OrchestratorMessage(
            session_id=session_id,
            role="assistant",
            content=reply,
        )
        db.add(assistant_msg)
        db.flush()

        db.commit()
        return assistant_msg

    except Exception:
        db.rollback()
        raise