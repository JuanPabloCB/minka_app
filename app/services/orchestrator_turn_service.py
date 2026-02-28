# app/services/orchestrator_turn_service.py
from __future__ import annotations

from uuid import UUID
from typing import Any

from sqlalchemy.orm import Session

from app.services.orchestrator_llm_service import call_orchestrator_llm
from app.services.orchestrator_messages_service import create_message
from app.db.models.orchestrator_message import OrchestratorMessage
from app.services.plans_service import create_draft_plan, list_plans_by_session


MAX_HISTORY_MESSAGES = 12  # total (user+assistant)


def _build_ui_hints(
    *,
    llm_result: dict[str, Any],
    meta_understood: bool,
    needs_confirmation: bool,
    cta_ready: bool,
) -> dict[str, Any]:
    """
    Genera hints para UI:
    - quick_replies (Sí/No) cuando estamos en confirmación final
    - tool_select cuando falta definir input/source
    - actions cuando el CTA ya está listo
    """
    hints: list[dict[str, Any]] = []

    missing_fields = llm_result.get("missing_fields") or []
    if not isinstance(missing_fields, list):
        missing_fields = []

    missing_fields_norm = {str(x).strip().lower() for x in missing_fields if str(x).strip()}

    # 1) Si falta el input/source (o similar), ofrecer selección
    #    Puedes ajustar los nombres según lo que tu prompt use.
    if any(k in missing_fields_norm for k in {"input", "inputs", "input_source", "source", "fuente", "canal"}):
        hints.append(
            {
                "type": "tool_select",
                "title": "¿De dónde viene tu información (input) por ahora?",
                "options": [
                    {"key": "gmail", "label": "Gmail", "value": "gmail", "enabled": True},
                    {"key": "drive", "label": "Google Drive", "value": "drive", "enabled": True},
                    {"key": "outlook", "label": "Outlook", "value": "outlook", "enabled": True},
                    {"key": "upload", "label": "Subir archivo", "value": "upload", "enabled": True},
                ],
                "meta": {"field": "input_source"},
            }
        )

    # 2) Si estamos en fase de confirmación final: quick replies
    #    (esto es EXACTAMENTE el “Sí/No” que quieres mientras chateas)
    if meta_understood and needs_confirmation and not cta_ready:
        hints.append(
            {
                "type": "quick_replies",
                "title": "¿Confirmas que esta es la meta correcta y que no falta nada?",
                "options": [
                    {"key": "confirm_yes", "label": "Sí, confirmado", "value": "Sí, confirmado.", "enabled": True},
                    {"key": "confirm_no", "label": "No, falta algo", "value": "No, falta algo.", "enabled": True},
                ],
                "meta": {"intent": "final_confirmation"},
            }
        )

    # 3) Si ya está listo el CTA: acciones para UI
    if cta_ready:
        hints.append(
            {
                "type": "actions",
                "title": "Siguiente paso",
                "options": [
                    {
                        "key": "go_analysts",
                        "label": "Ir a Analistas",
                        "value": "go_analysts",
                        "enabled": True,
                    }
                ],
                "meta": {"intent": "navigate", "target": "analysts"},
            }
        )

    return {"hints": hints}


def orchestrator_turn(db: Session, session_id: UUID, user_text: str) -> dict[str, Any]:
    # 1) Guardar user message
    user_msg = create_message(db, session_id=session_id, role="user", content=user_text)

    # 2) Traer historial completo (user + assistant)
    messages = (
        db.query(OrchestratorMessage)
        .filter(OrchestratorMessage.session_id == session_id)
        .order_by(OrchestratorMessage.created_at.asc())
        .all()
    )

    if len(messages) > MAX_HISTORY_MESSAGES:
        messages = messages[-MAX_HISTORY_MESSAGES:]

    history_messages = [
        {"role": m.role, "content": m.content}
        for m in messages
        if m.role in ("user", "assistant") and (m.content or "").strip()
    ]

    # 3) Llamar LLM
    llm_result = call_orchestrator_llm(history_messages)

    reply = llm_result.get("reply") or "No pude generar respuesta."
    meta_understood = bool(llm_result.get("meta_understood", False))

    try:
        confidence = float(llm_result.get("confidence", 0.0) or 0.0)
    except Exception:
        confidence = 0.0

    needs_confirmation = bool(llm_result.get("needs_confirmation", False))
    plan_title = (llm_result.get("plan_title") or "").strip()

    plan_steps = llm_result.get("plan_steps") or []
    if not isinstance(plan_steps, list):
        plan_steps = []
    plan_steps = [str(s).strip() for s in plan_steps if str(s).strip()]

    # 4) Guardar assistant message
    assistant_msg = create_message(db, session_id=session_id, role="assistant", content=reply)

    # 5) CTA + Plan
    is_confident = meta_understood and confidence >= 0.7

    cta_ready = False
    plan_created = False
    plan_id = None
    plan_status = None

    if is_confident and (not needs_confirmation):
        cta_ready = True

        existing_plans = list_plans_by_session(db, session_id=session_id)
        existing_draft = next((p for p in existing_plans if p.status == "draft"), None)

        if existing_draft:
            plan_id = existing_draft.id
            plan_status = existing_draft.status
        else:
            title = plan_title or "Ruta creada"
            result = create_draft_plan(
                db,
                session_id=session_id,
                title=title,
                steps_titles=plan_steps if plan_steps else None,
            )
            # create_draft_plan devuelve PlanCreateResult en tu versión nueva
            plan = getattr(result, "plan", result[0] if isinstance(result, tuple) else result)
            plan_created = True
            plan_id = plan.id
            plan_status = plan.status

    # 6) UI Hints (botones)
    ui_hints = _build_ui_hints(
        llm_result=llm_result,
        meta_understood=meta_understood,
        needs_confirmation=needs_confirmation,
        cta_ready=cta_ready,
    )

    return {
        "user_msg": user_msg,
        "assistant_msg": assistant_msg,
        "reply": reply,
        "cta_ready": cta_ready,
        "plan_created": plan_created,
        "plan_id": plan_id,
        "plan_status": plan_status,
        "ui_hints": ui_hints,
        # debug:
        "meta_understood": meta_understood,
        "needs_confirmation": needs_confirmation,
        "confidence": confidence,
    }