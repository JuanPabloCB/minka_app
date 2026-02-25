from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.services.orchestrator_messages_service import create_message
from app.services.plans_service import create_draft_plan

# 1) Aquí luego conectas tu LLM real.
def generate_assistant_reply(user_text: str) -> str:
    # Stub simple por ahora
    return (
        "Perfecto. Para ayudarte bien, dime:\n"
        "1) ¿Qué archivo/datos tienes?\n"
        "2) ¿Qué salida exacta quieres (reporte/KPIs/limpieza/comparativa)?\n"
        "3) ¿Algún filtro (fecha, región, producto)?"
    )

# 2) Regla MVP para activar el botón “Ruta Creada”
def is_context_minimum_reached(all_user_messages: list[str]) -> bool:
    # Heurística simple: si hay 1 mensaje largo o 2 mensajes medianos
    joined = " ".join(all_user_messages).strip()
    if len(joined) >= 40:
        return True
    if len(all_user_messages) >= 2 and sum(len(m) for m in all_user_messages) >= 40:
        return True
    return False


def orchestrator_turn(db: Session, session_id: UUID, user_text: str):
    """
    1) guarda msg user
    2) genera reply assistant (stub/LLM)
    3) guarda msg assistant
    4) decide cta_ready
    5) si cta_ready y aún no hay plan draft -> crea plan + steps
    """
    # 1) Guardar user message
    user_msg = create_message(db, session_id=session_id, role="user", content=user_text)

    # 2) Construir contexto mínimo (solo mensajes user por ahora)
    #    Usamos SQL directo via service de list? Si no tienes list en service,
    #    lo más rápido es leer con query acá.
    from app.db.models.orchestrator_message import OrchestratorMessage

    user_texts = [
        m.content
        for m in db.query(OrchestratorMessage)
        .filter(OrchestratorMessage.session_id == session_id)
        .filter(OrchestratorMessage.role == "user")
        .order_by(OrchestratorMessage.created_at.asc())
        .all()
    ]

    cta_ready = is_context_minimum_reached(user_texts)

    # 3) Reply assistant
    reply = generate_assistant_reply(user_text)

    assistant_msg = create_message(db, session_id=session_id, role="assistant", content=reply)

    # 4) Si cta_ready => crear plan draft (solo si no existe ya)
    plan_created = False
    plan_id = None
    plan_status = None

    if cta_ready:
        from app.db.models.plan import Plan  # ajusta al nombre real del modelo

        existing = (
            db.query(Plan)
            .filter(Plan.session_id == session_id)
            .order_by(Plan.created_at.desc())
            .first()
        )

        if not existing:
            # title básico: puedes mejorar luego
            plan, steps = create_draft_plan(db, session_id=session_id, title="Ruta creada por MinkaBot")
            plan_created = True
            plan_id = plan.id
            plan_status = plan.status
        else:
            plan_id = existing.id
            plan_status = existing.status

    return {
        "user_msg": user_msg,
        "assistant_msg": assistant_msg,
        "reply": reply,
        "cta_ready": cta_ready,
        "plan_created": plan_created,
        "plan_id": plan_id,
        "plan_status": plan_status,
    }