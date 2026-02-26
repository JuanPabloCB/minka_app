from uuid import UUID
from sqlalchemy.orm import Session

from app.services.orchestrator_llm_service import call_orchestrator_llm
from app.services.orchestrator_messages_service import create_message
from app.db.models.orchestrator_message import OrchestratorMessage


def orchestrator_turn(db: Session, session_id: UUID, user_text: str):
    # 1) Guardar user message
    user_msg = create_message(db, session_id=session_id, role="user", content=user_text)

    # 2) Traer historial (solo user por ahora)
    user_texts = [
        m.content
        for m in (
            db.query(OrchestratorMessage)
            .filter(OrchestratorMessage.session_id == session_id)
            .filter(OrchestratorMessage.role == "user")
            .order_by(OrchestratorMessage.created_at.asc())
            .all()
        )
    ]

    # Limitar historial para tokens
    MAX_HISTORY = 8
    if len(user_texts) > MAX_HISTORY:
        user_texts = user_texts[-MAX_HISTORY:]

    # 3) Llamar LLM real
    llm_result = call_orchestrator_llm(user_texts)

    reply = llm_result.get("reply", "No pude generar respuesta.")
    meta_understood = llm_result.get("meta_understood", False)
    confidence = llm_result.get("confidence", 0.0)

    # 4) Guardar assistant message
    assistant_msg = create_message(db, session_id=session_id, role="assistant", content=reply)

    # 5) Decidir CTA (botón negro)
    cta_ready = bool(meta_understood and confidence >= 0.7)

    # 6) Opción A: NO crear plan aquí
    return {
        "user_msg": user_msg,
        "assistant_msg": assistant_msg,
        "reply": reply,
        "cta_ready": cta_ready,
        "plan_created": False,
        "plan_id": None,
        "plan_status": None,
    }