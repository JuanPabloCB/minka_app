# app/services/orchestrator_turn_service.py
from __future__ import annotations

from uuid import UUID
from typing import Any

from sqlalchemy.orm import Session

from app.services.orchestrator_llm_service import call_orchestrator_llm
from app.services.orchestrator_messages_service import create_message
from app.db.models.orchestrator_message import OrchestratorMessage
from app.services.plans_service import create_draft_plan, list_plans_by_session
from app.core.constants import UI_BULLETS_CATALOG

import re

_CONFIRM_RE = re.compile(
    r"^\s*(sí[,.\s]*confirmado\.?|si[,.\s]*confirmado\.?|confirmo|confirmado|ok|dale|de acuerdo|correcto)\s*$",
    re.IGNORECASE,
)

_DECLINE_RE = re.compile(
    r"^\s*(no[,.\s]*falta algo\.?|falta algo|falta|cambia|corregir|corrige)\s*$",
    re.IGNORECASE,
)


MAX_HISTORY_MESSAGES = 12  # total (user+assistant)


def _is_user_confirming(user_text: str) -> bool:
    t = (user_text or "").strip()
    if not t:
        return False
    if _DECLINE_RE.match(t):
        return False
    return bool(_CONFIRM_RE.match(t))

def _focus_question_already_asked(history_messages: list[dict[str, str]]) -> bool:
    """
    Detecta si el bot ya preguntó por énfasis/prioridades (focus) en esta sesión.
    Lo hacemos por texto para no tocar DB.
    """
    needles = (
        "énfasis",
        "enfasis",
        "aspecto específico",
        "aspecto especifico",
        "prioridad",
        "prioridades",
        "algo en lo que",
        "algo específico",
        "algo especifico",
    )
    for m in reversed(history_messages):
        if m.get("role") != "assistant":
            continue
        txt = (m.get("content") or "").lower()
        if any(n in txt for n in needles):
            return True
    return False

def _build_ui_hints(
    *,
    llm_result: dict[str, Any],
    meta_understood: bool,
    needs_confirmation: bool,
    cta_ready: bool,  # lo dejamos por firma, pero NO lo usamos
) -> dict[str, Any]:
    missing_fields = llm_result.get("missing_fields") or []
    if not isinstance(missing_fields, list):
        missing_fields = []

    missing_norm = {str(x).strip().lower() for x in missing_fields if str(x).strip()}

    wants_input = any(k in missing_norm for k in {"input", "inputs", "input_source", "source", "fuente", "canal"})
    wants_output = any(k in missing_norm for k in {"output_format", "output", "formato_salida", "salida"})

    # 1) Prioridad: input_source (1 hint máximo)
    if wants_input:
        return {
            "hints": [
                {
                    "type": "tool_select",
                    "title": "¿De dónde viene tu información (input) por ahora?",
                    "options": [
                        {"key": "paste_text", "label": "Pegar texto en el chat", "value": "Voy a pegar texto en el chat", "enabled": True},
                        {"key": "local_upload", "label": "Subir archivo", "value": "Voy a subir un archivo local", "enabled": True},
                        {"key": "google_drive", "label": "Google Drive", "value": "Voy a usar Google Drive", "enabled": True},
                    ],
                    "meta": {"field": "input_source"},
                }
            ]
        }

    # 2) Luego output_format (1 hint máximo)
    if wants_output:
        return {
            "hints": [
                {
                    "type": "tool_select",
                    "title": "¿En qué formato quieres el resultado?",
                    "options": [
                        {"key": "pdf", "label": "PDF", "value": "Lo quiero en formato PDF", "enabled": True},
                        {"key": "docx", "label": "Word (.docx)", "value": "Lo quiero en formato Word (.docx)", "enabled": True},
                    ],
                    "meta": {"field": "output_format"},
                }
            ]
        }

    # 3) Confirmación final (1 hint máximo)
    if meta_understood and needs_confirmation and not cta_ready:
        return {
            "hints": [
                {
                    "type": "quick_replies",
                    "title": "¿Confirmas que esta es la meta correcta y que no falta nada?",
                    "options": [
                        {"key": "confirm_yes", "label": "Sí, confirmado", "value": "Sí, confirmado.", "enabled": True},
                        {"key": "confirm_no", "label": "No, falta algo", "value": "No, falta algo.", "enabled": True},
                    ],
                    "meta": {"intent": "final_confirmation"},
                }
            ]
        }

    # 4) default
    return {"hints": []}


# bullets
def _catalog_bullets(key: str) -> dict[str, Any] | None:
    data = UI_BULLETS_CATALOG.get(key)
    if not data:
        return None
    items = data.get("items") or []
    return {
        "title": data.get("title"),
        "variant": data.get("variant", "bullets"),
        "items": [{"key": f"{key}_{i+1}", "label": str(x)} for i, x in enumerate(items) if str(x).strip()],
    }


def _build_ui_bullets(
    *,
    llm_result: dict[str, Any],
    meta_understood: bool,
    needs_confirmation: bool,
    cta_ready: bool,
) -> dict[str, Any] | None:
    # 1) Confirmación (IA)
    if meta_understood and needs_confirmation and not cta_ready:
        items = llm_result.get("ui_bullets_items") or llm_result.get("understanding_steps") or []
        if not isinstance(items, list):
            items = []
        items = [str(x).strip() for x in items if str(x).strip()]
        if not items:
            return None
        return {
            "title": "Parece que quieres:",
            "variant": "timeline",
            "items": [{"key": f"step_{i+1}", "label": text} for i, text in enumerate(items)],
        }

    # 2) Bullets fijos por KEY explícita
    bullets_key = llm_result.get("ui_bullets_key")
    if isinstance(bullets_key, str) and bullets_key.strip():
        block = _catalog_bullets(bullets_key.strip())
        if block:
            return block

    # 3) Bullets fijos por ESTADO (si falta input/source)
    missing_fields = llm_result.get("missing_fields") or []
    if not isinstance(missing_fields, list):
        missing_fields = []
    missing_norm = {str(x).strip().lower() for x in missing_fields if str(x).strip()}

    wants_input = any(k in missing_norm for k in {"input", "inputs", "input_source", "source", "fuente", "canal"})
    if wants_input:
        return _catalog_bullets("available_inputs")

    wants_output = any(k in missing_norm for k in {"output_format", "output", "formato_salida", "salida"})
    if wants_output:
        return _catalog_bullets("supported_output_formats")

    return None


def orchestrator_turn(db: Session, session_id: UUID, user_text: str) -> dict[str, Any]:
    # 1) Guardar user message
    user_msg = create_message(db, session_id=session_id, role="user", content=user_text, meta={},)

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
    needs_confirmation = bool(llm_result.get("needs_confirmation", False))
    user_confirmed = _is_user_confirming(user_text)

    # --- NORMALIZA missing_fields a nombres canónicos ---
    raw_missing = llm_result.get("missing_fields") or []
    if not isinstance(raw_missing, list):
        raw_missing = []
    raw_norm = {str(x).strip().lower() for x in raw_missing if str(x).strip()}

    canonical_missing: set[str] = set()

    # goal_intent (si lo usas en prompt)
    if raw_norm & {"goal_intent", "meta", "goal"}:
        canonical_missing.add("goal_intent")

    # document_type / analysis_goal / focus
    if raw_norm & {"document_type", "tipo_documento", "tipo_contrato"}:
        canonical_missing.add("document_type")
    if raw_norm & {"analysis_goal", "objetivo_analisis"}:
        canonical_missing.add("analysis_goal")
    if raw_norm & {"focus", "enfasis", "prioridades"}:
        canonical_missing.add("focus")

    # input / output
    if raw_norm & {"input", "inputs", "input_source", "source", "fuente", "canal"}:
        canonical_missing.add("input_source")
    if raw_norm & {"output", "output_format", "formato_salida", "salida"}:
        canonical_missing.add("output_format")

    # --- GUARDRAIL por ui_context (pero SIN romper el orden del flujo) ---
    ui_ctx = llm_result.get("ui_context") or {}
    if not isinstance(ui_ctx, dict):
        ui_ctx = {}

    def _has(v: Any) -> bool:
        return isinstance(v, str) and v.strip()

    # Calidad doc/analysis: solo si ya estamos en meta_understood (ya hay intención)
    if meta_understood:
        doc = (ui_ctx.get("document_type") or "").strip().lower() if isinstance(ui_ctx.get("document_type"), str) else ""
        ag = (ui_ctx.get("analysis_goal") or "").strip().lower() if isinstance(ui_ctx.get("analysis_goal"), str) else ""

        # document_type no puede ser genérico
        if not doc or doc in {"documento", "contrato", "archivo", "texto"}:
            canonical_missing.add("document_type")

        # analysis_goal no puede ser genérico
        if not ag or ag in {"analizar", "revisar", "ver"}:
            canonical_missing.add("analysis_goal")

        # focus: NO es obligatorio. Solo lo pedimos si el prompt lo marca.
        # Si tu LLM devuelve missing_fields=["focus"], lo respetamos.
        # Si no, no lo forzamos aquí.

        # 👇 IMPORTANTE: input/output SOLO se piden cuando ya tenemos doc + analysis_goal OK
        doc_ok = doc and doc not in {"documento", "contrato", "archivo", "texto"}
        ag_ok = ag and ag not in {"analizar", "revisar", "ver"}

        if doc_ok and ag_ok:
            if not _has(ui_ctx.get("input_source")):
                canonical_missing.add("input_source")
            if not _has(ui_ctx.get("output_format")):
                canonical_missing.add("output_format")

    llm_result["missing_fields"] = sorted(canonical_missing)

    # --- GUARDRAIL: no permitir confirmación si falta algo ---
    if llm_result["missing_fields"]:
        llm_result["needs_confirmation"] = False
        needs_confirmation = False

    # ---------------------------
    # ---------------------------
    # FORZAR pregunta de foco ANTES de input/output (una sola vez)
    # ---------------------------
    ui_ctx = llm_result.get("ui_context") or {}
    if not isinstance(ui_ctx, dict):
        ui_ctx = {}

    doc = (ui_ctx.get("document_type") or "").strip().lower() if isinstance(ui_ctx.get("document_type"), str) else ""
    ag = (ui_ctx.get("analysis_goal") or "").strip().lower() if isinstance(ui_ctx.get("analysis_goal"), str) else ""

    doc_ok = bool(doc) and doc not in {"documento", "contrato", "archivo", "texto"}
    ag_ok = bool(ag) and ag not in {"analizar", "revisar", "ver"}

    # ¿Ya se preguntó enfoque antes?
    focus_asked = _focus_question_already_asked(history_messages)

    # Si ya tenemos doc+analysis OK y todavía no se preguntó enfoque,
    # este turno SOLO pregunta focus (y NO deja pasar a input/output).
    if meta_understood and doc_ok and ag_ok and not focus_asked:
        llm_result["needs_confirmation"] = False
        needs_confirmation = False

        llm_result["missing_fields"] = ["focus"]  # <- SOLO focus, nada más
        llm_result["reply"] = "¿Hay algún énfasis adicional que quieras agregar?"
        reply = llm_result["reply"]

    missing_norm = set(llm_result.get("missing_fields") or [])

    # Reply coherente con el paso actual (solo para input/output)
    if "input_source" in missing_norm:
        llm_result["reply"] = "¿Cómo vas a enviar o cargar el documento?"
    elif "output_format" in missing_norm:
        llm_result["reply"] = "¿En qué formato quieres el resultado?"

    reply = llm_result.get("reply") or reply

    # helper norm para condiciones posteriores
    missing_fields = llm_result.get("missing_fields") or []
    if not isinstance(missing_fields, list):
        missing_fields = []
    missing_fields_norm = [str(x).strip() for x in missing_fields if str(x).strip()]

    # ✅ OVERRIDE server-side para evitar loop:
    if user_confirmed and meta_understood and not missing_fields_norm:
        llm_result["needs_confirmation"] = False
        needs_confirmation = False

        reply = "Listo. Ruta confirmada."
        llm_result["reply"] = reply

        llm_result["understanding_steps"] = []

    # --- clamp: si hay UI (hints/bullets), reply debe ser corto ---
    has_ui_reason = bool(missing_fields_norm) or bool(llm_result.get("needs_confirmation", False))
    if has_ui_reason and isinstance(reply, str):
        reply = reply.strip()
        if len(reply) > 80:
            cut = reply.split(".")[0].strip()
            reply = (cut + ".") if cut else reply[:80].rstrip() + "…"
            llm_result["reply"] = reply

    try:
        confidence = float(llm_result.get("confidence", 0.0) or 0.0)
    except Exception:
        confidence = 0.0

    plan_title = (llm_result.get("plan_title") or "").strip()

    plan_steps = llm_result.get("plan_steps") or []
    if not isinstance(plan_steps, list):
        plan_steps = []
    plan_steps = [str(s).strip() for s in plan_steps if str(s).strip()]


    # 5) CTA + Plan (solo si user confirmó y no falta nada)
    cta_ready = False
    plan_created = False
    plan_id = None
    plan_status = None

    if user_confirmed and meta_understood and not missing_fields_norm:
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

    # 7) UI Bullets (lista/timeline)
    ui_bullets = _build_ui_bullets(
        llm_result=llm_result,
        meta_understood=meta_understood,
        needs_confirmation=needs_confirmation,
        cta_ready=cta_ready,
    )

        # 4) Guardar assistant message
    assistant_meta = {
    "ui_hints": ui_hints,
    "ui_bullets": ui_bullets,
    "ui_context": llm_result.get("ui_context"),
    "meta_understood": meta_understood,
    "missing_fields": missing_fields_norm,
    "needs_confirmation": needs_confirmation,
    "understanding_steps": llm_result.get("understanding_steps") or [],
    "confidence": confidence,
    "cta_ready": cta_ready,
    "plan_created": plan_created,
    "plan_id": str(plan_id) if plan_id else None,
    "plan_status": plan_status,
    }

    assistant_msg = create_message(
    db,
    session_id=session_id,
    role="assistant",
    content=reply,
    meta=assistant_meta,
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
        "ui_bullets": ui_bullets,
        "ui_context": llm_result.get("ui_context"),
        # debug:
        "meta_understood": meta_understood,
        "needs_confirmation": needs_confirmation,
        "confidence": confidence,
    }