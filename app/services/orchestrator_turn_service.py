# app/services/orchestrator_turn_service.py
from __future__ import annotations

from uuid import UUID
from typing import Any

from sqlalchemy.orm import Session

from app.services.orchestrator_llm_service import call_orchestrator_llm
from app.services.orchestrator_messages_service import create_message
from app.db.models.orchestrator_message import OrchestratorMessage
from app.db.models.orchestrator_session import OrchestratorSession
from app.db.models.uploaded_file import UploadedFile
from app.services.plans_service import create_draft_plan, list_plans_by_session
from app.core.constants import (
    UI_BULLETS_CATALOG,
    SUPPORTED_INPUT_SOURCES,
    SUPPORTED_OUTPUT_FORMATS,
)

import re

_CONFIRM_RE = re.compile(
    r"^\s*(sí[,.\s]*confirmado\.?|si[,.\s]*confirmado\.?|confirmo|confirmado|ok|dale|de acuerdo|correcto|afirmativo|afirmativa|yes|ya|claro)\s*$",
    re.IGNORECASE,
)

_DECLINE_RE = re.compile(
    r"^\s*(no[,.\s]*falta algo\.?|falta algo|falta|cambia|corregir|corrige|me equivoqué|me equivoque|me confundí|me confundi)\s*$",
    re.IGNORECASE,
)


MAX_HISTORY_MESSAGES = 16  # total (user+assistant)

def _normalize_input_source(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    key = value.strip().lower()

    direct = SUPPORTED_INPUT_SOURCES.get(key)
    if direct:
        return direct

#    if (
#        "google drive" in key
#        or "gdrive" in key
#        or key == "drive"
#        or "por drive" in key
#        or "usar google drive" in key
#        or "usaré google drive" in key
#        or "usare google drive" in key
#    ):
#        return "google_drive"

    if (
        "subir" in key
        or "archivo local" in key
        or "desde mi computadora" in key
        or "desde mi pc" in key
        or "archivo desde mi computadora" in key
        or "archivo desde mi pc" in key
    ):
        return "local_upload"

#    if "pegar" in key or "texto" in key or "chat" in key:
#        return "paste_text"

    if (
        "aún no lo tengo" in key
        or "aun no lo tengo" in key
        or "todavía no lo tengo" in key
        or "todavia no lo tengo" in key
        or "no lo tengo aún" in key
        or "no lo tengo aun" in key
    ):
        return "pending"

    return None


def _normalize_output_format(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    key = value.strip().lower()
    return SUPPORTED_OUTPUT_FORMATS.get(key)

def _normalize_result_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    key = value.strip().lower()

    mapping = {
        "documento resaltado": "highlighted_document",
        "documento highlight": "highlighted_document",
        "highlighted_document": "highlighted_document",
        "highlight": "highlighted_document",
        "informe": "analysis_report",
        "analysis_report": "analysis_report",
        "reporte": "analysis_report",
        "resumen ejecutivo": "executive_summary",
        "executive_summary": "executive_summary",
        "explicación": "in_app_explanation",
        "explicacion": "in_app_explanation",
        "in_app_explanation": "in_app_explanation",
        "dashboard": "dashboard_view",
        "dashboard_view": "dashboard_view",
    }

    return mapping.get(key)

def _is_upload_now_response(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    valid = {
        "subir ahora",
        "quiero subirlo ahora",
        "voy a subirlo ahora",
        "subir archivo ahora",
        "subir archivo",
        "subir mi archivo",
    }
    return t in valid


def _is_upload_later_response(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    if not t:
        return False

    valid = {
        "lo haré después",
        "lo hare despues",
        "lo subiré después",
        "lo subire despues",
        "después",
        "despues",
        "aún no lo haré",
        "aun no lo hare",
        "upload_later",
    }

    return t in valid or t.startswith("lo har") or t.startswith("aún no") or t.startswith("aun no")


def _is_user_declining(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    if not t:
        return False

    decline_prefixes = (
        "no",
        "falta",
        "cambia",
        "corrige",
        "corregir",
        "me equivoqué",
        "me equivoque",
        "me confundí",
        "me confundi",
        "olvidé",
        "olvide",
        "quiero cambiar",
        "quiero corregir",
    )
    return any(t.startswith(x) for x in decline_prefixes)

def _is_focus_none_response(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    if not t:
        return False

    valid = {
        "no",
        "ninguno",
        "ninguna",
        "ningún énfasis",
        "ningun enfasis",
        "sin énfasis",
        "sin enfasis",
        "no tengo",
        "no tengo ninguno",
        "ningún foco",
        "ningun foco",
    }
    return t in valid


def _mentions_output_change(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    keywords = (
        "pdf",
        ".pdf",
        "docx",
        ".docx",
        "word",
        "formato",
        "resultado",
        "output",
    )
    return any(k in t for k in keywords)


def _mentions_input_change(user_text: str) -> bool:
    t = (user_text or "").strip().lower()

    # Solo detectamos cambios reales de canal/fuente de entrada.
    # Ojo: NO usar palabras genéricas como "documento" o "archivo",
    # porque aparecen en mensajes normales del flujo y rompen la persistencia.
    keywords = (
        "subir archivo",
        "subir un archivo",
        "archivo local",
        "voy a subir un archivo local",
        "input",
    )
    return any(k in t for k in keywords)


def _mentions_document_type_change(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    keywords = (
        "contrato",
        "nda",
        "arrendamiento",
        "laboral",
        "compraventa",
        "tipo de documento",
    )
    return any(k in t for k in keywords)


def _mentions_analysis_goal_change(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    keywords = (
        "informe",
        "resumen",
        "riesgo",
        "riesgos",
        "cláusula",
        "clausula",
        "penalidad",
        "penalidades",
        "objetivo",
    )
    return any(k in t for k in keywords)

def _get_last_assistant_meta(messages: list[OrchestratorMessage]) -> dict[str, Any]:
    for m in reversed(messages):
        if m.role != "assistant":
            continue
        meta = m.meta or {}
        if isinstance(meta, dict):
            return meta
    return {}

def _get_active_missing_field(last_assistant_meta: dict[str, Any]) -> str | None:
    missing = last_assistant_meta.get("missing_fields") or []
    if not isinstance(missing, list):
        return None

    ordered_priority = [
        "goal_intent",
        "document_type",
        "analysis_goal",
        "focus",
        "input_source",
        "file_intake",
        "result_type",
        "output_format",
    ]

    missing_norm = [str(x).strip() for x in missing if str(x).strip()]
    for field in ordered_priority:
        if field in missing_norm:
            return field
    return None

def _resolve_active_step(
    *,
    missing_fields: list[str],
    needs_confirmation: bool,
    confirmation_state: str,
) -> str:
    if confirmation_state == "editing":
        return "confirmation_edit"

    if needs_confirmation:
        return "confirmation"

    ordered = [
        "goal_intent",
        "document_type",
        "analysis_goal",
        "focus",
        "input_source",
        "file_intake",
        "result_type",
        "output_format",  # transicional / legacy
    ]

    normalized = [str(x).strip() for x in (missing_fields or []) if str(x).strip()]
    for step in ordered:
        if step in normalized:
            return step

    return "goal_intent"


def _resolve_interaction_mode(active_step: str, confirmation_state: str) -> str:
    if confirmation_state == "editing" or active_step == "confirmation_edit":
        return "review_edit"

    if confirmation_state == "awaiting_confirmation" or active_step == "confirmation":
        return "hint_required"

    if active_step == "input_source":
        return "hint_required"

    if active_step == "file_intake":
        return "hint_required"

    if active_step == "result_type":
        return "guided_options"

    return "free_text"

def _reply_for_active_step(active_step: str, confirmation_state: str) -> str:
    if confirmation_state == "editing" or active_step == "confirmation_edit":
        return "¿Qué quieres corregir o completar?"

    mapping = {
        "goal_intent": "¿Cuál es tu objetivo principal?",
        "document_type": "¿Qué tipo de documento específico vas a analizar?",
        "analysis_goal": "¿Qué resultado esperas obtener del análisis?",
        "focus": "¿Hay algún énfasis adicional que quieras agregar?",
        "input_source": "¿Cómo vas a enviar o cargar el documento?",
        "file_intake": "Sube tu archivo aquí.",
        "result_type": "¿Qué tipo de resultado esperas?",
        "confirmation": "Resumen listo, revisa los pasos antes de continuar.",
    }
    return mapping.get(active_step, "¿Me das un poco más de contexto?")

def _merge_focus(previous_focus: Any, current_focus: Any) -> list[str]:
    prev = [str(x).strip() for x in (previous_focus or []) if str(x).strip()]
    curr = [str(x).strip() for x in (current_focus or []) if str(x).strip()]

    if not curr:
        return prev

    merged: list[str] = []
    seen: set[str] = set()

    for item in curr:
        key = item.lower()
        if key not in seen:
            merged.append(item)
            seen.add(key)

    for item in prev:
        key = item.lower()
        if key not in seen:
            merged.append(item)
            seen.add(key)

    return merged[:5]


def _merge_ui_context(previous_ctx: dict[str, Any] | None, current_ctx: dict[str, Any] | None) -> dict[str, Any]:
    previous_ctx = previous_ctx or {}
    current_ctx = current_ctx or {}

    def _pick_str(field: str) -> str | None:
        cur = current_ctx.get(field)
        if isinstance(cur, str) and cur.strip():
            return cur.strip()

        prev = previous_ctx.get(field)
        if isinstance(prev, str) and prev.strip():
            return prev.strip()

        return None

    def _pick_bool(field: str) -> bool | None:
        cur = current_ctx.get(field)
        if isinstance(cur, bool):
            return cur

        prev = previous_ctx.get(field)
        if isinstance(prev, bool):
            return prev

        return None

    return {
        "task_type": _pick_str("task_type"),
        "document_type": _pick_str("document_type"),
        "analysis_goal": _pick_str("analysis_goal"),
        "input_source": _pick_str("input_source"),
        "input_file_name": _pick_str("input_file_name"),
        "uploaded_file_id": current_ctx.get("uploaded_file_id") or previous_ctx.get("uploaded_file_id"),
        "file_uploaded": _pick_bool("file_uploaded"),
        "upload_deferred": _pick_bool("upload_deferred"),
        "file_validation_status": _pick_str("file_validation_status"),
        "output_format": _pick_str("output_format"),  # transicional / legacy
        "result_type": _pick_str("result_type"),
        "focus": _merge_focus(previous_ctx.get("focus"), current_ctx.get("focus")),
    }


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
    active_step: str,
    needs_confirmation: bool,
    cta_ready: bool,
) -> dict[str, Any]:
    if active_step == "input_source":
        return {
            "hints": [
                {
                    "type": "tool_select",
                    "title": "¿De dónde viene tu información (input) por ahora?",
                    "options": [
                        #{"key": "paste_text", "label": "Pegar texto en el chat", "value": "Voy a pegar texto en el chat", "enabled": True},
                        {"key": "local_upload", "label": "Subir archivo local", "value": "Voy a subir un archivo local", "enabled": True},
                        #{"key": "google_drive", "label": "Google Drive", "value": "Voy a usar Google Drive", "enabled": True},
                        {"key": "pending", "label": "Aún no lo tengo", "value": "Aún no lo tengo"}
                    ],
                    "meta": {"field": "input_source"},
                }
            ]
        }
    
    if active_step == "file_intake":
        return {
            "hints": [
                {
                    "type": "actions",
                    "title": "Sube tu archivo aquí",
                    "options": [
                        {
                            "key": "upload_now",
                            "label": "Subir archivo ahora",
                            "value": "Subir ahora",
                            "enabled": True,
                            "reason": None,
                        },
                        {
                            "key": "upload_later",
                            "label": "Lo haré después",
                            "value": "Lo haré después",
                            "enabled": True,
                            "reason": None,
                        },
                    ],
                    "meta": {"field": "file_intake"},
                }
            ]
        }

    if active_step == "result_type":
        return {
            "hints": [
                {
                    "type": "tool_select",
                    "title": "¿Qué tipo de resultado esperas?",
                    "options": [
                        {"key": "highlighted_document", "label": "Documento resaltado", "value": "Quiero un documento resaltado", "enabled": True},
                        {"key": "analysis_report", "label": "Informe", "value": "Quiero un informe", "enabled": True},
                        {"key": "executive_summary", "label": "Resumen ejecutivo", "value": "Quiero un resumen ejecutivo", "enabled": True},
                        {"key": "in_app_explanation", "label": "Explicación en la app", "value": "Quiero una explicación en la app", "enabled": True},
                    ],
                    "meta": {"field": "result_type"},
                }
            ]
        }

    if active_step == "confirmation" and needs_confirmation and not cta_ready:
        return {
            "hints": [
                {
                    "type": "quick_replies",
                    "title": "¿Confirmas que esta es la meta correcta y que no falta nada?",
                    "options": [
                        {"key": "confirm_yes", "label": "Sí, confirmado", "value": "Sí, confirmado.", "enabled": True},
                        {"key": "confirm_no", "label": "No, falta/quiero cambiar algo", "value": "No, falta/quiero cambiar algo.", "enabled": True},
                    ],
                    "meta": {"intent": "final_confirmation"},
                }
            ]
        }

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
    active_step: str,
    llm_result: dict[str, Any],
    needs_confirmation: bool,
    cta_ready: bool,
) -> dict[str, Any] | None:
    if active_step == "confirmation" and needs_confirmation and not cta_ready:
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

    if active_step == "input_source":
        return _catalog_bullets("available_inputs")

    return None

def _humanize_result_type(result_type: str | None) -> str:
    mapping = {
        "highlighted_document": "documento resaltado",
        "analysis_report": "informe",
        "executive_summary": "resumen ejecutivo",
        "in_app_explanation": "explicación en la app",
        "dashboard_view": "dashboard",
    }
    return mapping.get(result_type or "", "resultado")


def _build_understanding_steps_from_ui_context(ui_ctx: dict[str, Any]) -> list[str]:
    steps: list[str] = []

    document_type = ui_ctx.get("document_type")
    analysis_goal = ui_ctx.get("analysis_goal")
    input_source = ui_ctx.get("input_source")
    input_file_name = ui_ctx.get("input_file_name")
    result_type = ui_ctx.get("result_type")
    focus = ui_ctx.get("focus") or []

    if isinstance(document_type, str) and document_type.strip():
        steps.append(f"Analizar el {document_type.strip()}")

    if isinstance(analysis_goal, str) and analysis_goal.strip():
        steps.append(capitalize_first_text(analysis_goal.strip()))

    if isinstance(focus, list):
        for item in focus:
            if isinstance(item, str) and item.strip():
                steps.append(f"Considerar especialmente {item.strip()}")

    if input_source == "local_upload" and isinstance(input_file_name, str) and input_file_name.strip():
        steps.append(f"Trabajar con el archivo {input_file_name.strip()}")

    if isinstance(result_type, str) and result_type.strip():
        steps.append(f"Preparar un {_humanize_result_type(result_type)}")

    return steps[:5]


def capitalize_first_text(value: str) -> str:
    if not value:
        return value
    return value[0].upper() + value[1:]


def _recompute_missing_fields_from_ui_context(ui_ctx: dict[str, Any]) -> list[str]:
    missing: list[str] = []

    def _has(v: Any) -> bool:
        return isinstance(v, str) and v.strip()

    if not _has(ui_ctx.get("document_type")):
        missing.append("document_type")

    if not _has(ui_ctx.get("analysis_goal")):
        missing.append("analysis_goal")

    if not _has(ui_ctx.get("input_source")):
        missing.append("input_source")

    if (
        _normalize_input_source(ui_ctx.get("input_source")) == "local_upload"
        and ui_ctx.get("file_uploaded") is not True
        and ui_ctx.get("upload_deferred") is not True
    ):
        missing.append("file_intake")

    if not _normalize_result_type(ui_ctx.get("result_type")):
        missing.append("result_type")

    return missing

def complete_file_intake_turn(
    db: Session,
    *,
    session_id: UUID,
    uploaded_file_id: UUID,
) -> dict[str, Any]:
    session_obj = (
        db.query(OrchestratorSession)
        .filter(OrchestratorSession.id == session_id)
        .first()
    )
    if not session_obj:
        raise ValueError("SESSION_NOT_FOUND")

    uploaded_file = (
        db.query(UploadedFile)
        .filter(
            UploadedFile.id == uploaded_file_id,
            UploadedFile.session_id == session_id,
        )
        .first()
    )
    if not uploaded_file:
        raise ValueError("UPLOADED_FILE_NOT_FOUND")

    if uploaded_file.validation_status != "accepted":
        raise ValueError("UPLOADED_FILE_NOT_ACCEPTED")

    messages = (
        db.query(OrchestratorMessage)
        .filter(OrchestratorMessage.session_id == session_id)
        .order_by(OrchestratorMessage.created_at.asc())
        .all()
    )

    if len(messages) > MAX_HISTORY_MESSAGES:
        messages = messages[-MAX_HISTORY_MESSAGES:]

    last_assistant_meta = _get_last_assistant_meta(messages)
    previous_ui_ctx = last_assistant_meta.get("ui_context") or {}
    if not isinstance(previous_ui_ctx, dict):
        previous_ui_ctx = {}

    merged_ui_ctx = _merge_ui_context(
        previous_ui_ctx,
        {
            "input_source": "local_upload",
            "input_file_name": uploaded_file.original_filename,
            "uploaded_file_id": str(uploaded_file.id),
            "file_uploaded": True,
            "file_validation_status": uploaded_file.validation_status,
            "upload_deferred": False,
        },
    )

    meta_understood = bool(last_assistant_meta.get("meta_understood", True))
    confidence = float(last_assistant_meta.get("confidence", 1.0) or 1.0)
    focus_asked_once = bool(last_assistant_meta.get("focus_asked_once", False))

    missing_fields_norm = _recompute_missing_fields_from_ui_context(merged_ui_ctx)

    needs_confirmation = bool(meta_understood and not missing_fields_norm)
    confirmation_state = "awaiting_confirmation" if needs_confirmation else "none"

    active_step = _resolve_active_step(
        missing_fields=missing_fields_norm,
        needs_confirmation=needs_confirmation,
        confirmation_state=confirmation_state,
    )
    interaction_mode = _resolve_interaction_mode(
        active_step=active_step,
        confirmation_state=confirmation_state,
    )

    reply = _reply_for_active_step(active_step, confirmation_state)

    understanding_steps = (
        _build_understanding_steps_from_ui_context(merged_ui_ctx)
        if active_step == "confirmation" and needs_confirmation
        else []
    )

    ui_hints = _build_ui_hints(
        active_step=active_step,
        needs_confirmation=needs_confirmation,
        cta_ready=False,
    )

    ui_bullets = _build_ui_bullets(
        active_step=active_step,
        llm_result={"understanding_steps": understanding_steps},
        needs_confirmation=needs_confirmation,
        cta_ready=False,
    )

    assistant_meta = {
        "ui_hints": ui_hints,
        "ui_bullets": ui_bullets,
        "ui_context": merged_ui_ctx,
        "meta_understood": meta_understood,
        "missing_fields": missing_fields_norm,
        "needs_confirmation": needs_confirmation,
        "understanding_steps": understanding_steps,
        "confidence": confidence,
        "cta_ready": False,
        "plan_created": False,
        "plan_id": None,
        "plan_status": None,
        "active_step": active_step,
        "interaction_mode": interaction_mode,
        "confirmation_state": confirmation_state,
        "focus_asked_once": focus_asked_once,
    }

    assistant_msg = create_message(
        db,
        session_id=session_id,
        role="assistant",
        content=reply,
        meta=assistant_meta,
    )

    return {
        "assistant_msg": assistant_msg,
        "reply": reply,
        "active_step": active_step,
        "interaction_mode": interaction_mode,
        "confirmation_state": confirmation_state,
        "cta_ready": False,
        "plan_created": False,
        "plan_id": None,
        "plan_status": None,
        "ui_hints": ui_hints,
        "ui_bullets": ui_bullets,
        "ui_context": merged_ui_ctx,
    }

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

    last_assistant_meta = _get_last_assistant_meta(messages)
    active_missing_field = _get_active_missing_field(last_assistant_meta)
    focus_asked_once = bool(last_assistant_meta.get("focus_asked_once", False))

    previous_ui_ctx = last_assistant_meta.get("ui_context") or {}

    if not isinstance(previous_ui_ctx, dict):
        previous_ui_ctx = {}

    current_ui_ctx = llm_result.get("ui_context") or {}
    if not isinstance(current_ui_ctx, dict):
        current_ui_ctx = {}

    merged_ui_ctx = _merge_ui_context(previous_ui_ctx, current_ui_ctx)

    # Validación dura de catálogos soportados
    raw_input_source = merged_ui_ctx.get("input_source")
    raw_output_format = merged_ui_ctx.get("output_format")

    normalized_input_source = _normalize_input_source(raw_input_source)
    normalized_output_format = _normalize_output_format(raw_output_format)

    inferred_input_from_user = _normalize_input_source(user_text)
    if not normalized_input_source and inferred_input_from_user:
        normalized_input_source = inferred_input_from_user

    if raw_input_source is not None and normalized_input_source is None:
        prev_valid_input = _normalize_input_source(previous_ui_ctx.get("input_source"))
        merged_ui_ctx["input_source"] = prev_valid_input
    else:
        merged_ui_ctx["input_source"] = normalized_input_source

    if raw_output_format is not None and normalized_output_format is None:
        prev_valid_output = _normalize_output_format(previous_ui_ctx.get("output_format"))
        merged_ui_ctx["output_format"] = prev_valid_output
    else:
        merged_ui_ctx["output_format"] = normalized_output_format

    generic_document_types = {"documento", "contrato", "archivo", "texto"}
    generic_analysis_goals = {"analizar", "revisar", "ver"}

    prev_doc = previous_ui_ctx.get("document_type")
    prev_goal = previous_ui_ctx.get("analysis_goal")
    prev_input = _normalize_input_source(previous_ui_ctx.get("input_source"))
    prev_output = _normalize_output_format(previous_ui_ctx.get("output_format"))
    prev_result_type = _normalize_result_type(previous_ui_ctx.get("result_type"))

    # Limpiar genéricos del turno actual
    if isinstance(merged_ui_ctx.get("document_type"), str):
        doc_tmp = merged_ui_ctx["document_type"].strip().lower()
        if doc_tmp in generic_document_types:
            merged_ui_ctx["document_type"] = None

    if isinstance(merged_ui_ctx.get("analysis_goal"), str):
        ag_tmp = merged_ui_ctx["analysis_goal"].strip().lower()
        if ag_tmp in generic_analysis_goals:
            merged_ui_ctx["analysis_goal"] = None

    document_type_changed = (
        isinstance(prev_doc, str)
        and prev_doc.strip()
        and isinstance(merged_ui_ctx.get("document_type"), str)
        and merged_ui_ctx["document_type"].strip()
        and merged_ui_ctx["document_type"].strip().lower() != prev_doc.strip().lower()
    )

    # Congelar campos ya establecidos salvo corrección explícita del user
    if isinstance(prev_doc, str) and prev_doc.strip() and not _mentions_document_type_change(user_text):
        merged_ui_ctx["document_type"] = prev_doc.strip()

    if isinstance(prev_goal, str) and prev_goal.strip() and not _mentions_analysis_goal_change(user_text):
        merged_ui_ctx["analysis_goal"] = prev_goal.strip()

    # Si el turno actual no está cambiando explícitamente el input, conserva el input previo válido
    if prev_input and not _mentions_input_change(user_text):
        merged_ui_ctx["input_source"] = prev_input

    if prev_output and not _mentions_output_change(user_text):
        merged_ui_ctx["output_format"] = prev_output

    current_result_type = _normalize_result_type(merged_ui_ctx.get("result_type"))
    if prev_result_type and not current_result_type:
        merged_ui_ctx["result_type"] = prev_result_type

    # Si cambió realmente el tipo de documento, conserva input/output,
    # pero permite revalidar analysis_goal sin desarmar todo el contexto.
    if document_type_changed:
        merged_ui_ctx["input_source"] = prev_input
        merged_ui_ctx["output_format"] = prev_output

    # Congelación dura final:
    # si ya existía un valor válido previo y el turno actual no pidió cambiarlo,
    # no permitimos que quede en null por ruido del LLM.
    if prev_input and not _mentions_input_change(user_text) and not merged_ui_ctx.get("input_source"):
        merged_ui_ctx["input_source"] = prev_input

    if isinstance(prev_doc, str) and prev_doc.strip() and not _mentions_document_type_change(user_text) and not merged_ui_ctx.get("document_type"):
        merged_ui_ctx["document_type"] = prev_doc.strip()

    if isinstance(prev_goal, str) and prev_goal.strip() and not _mentions_analysis_goal_change(user_text) and not merged_ui_ctx.get("analysis_goal"):
        merged_ui_ctx["analysis_goal"] = prev_goal.strip()

    if prev_result_type and not _normalize_result_type(merged_ui_ctx.get("result_type")):
        merged_ui_ctx["result_type"] = prev_result_type
    
    # Protección extra del input_source:
    # si ya existía uno válido previo y el usuario no está cambiando explícitamente
    # la fuente de entrada, jamás permitir que vuelva a null.
    if prev_input and not _mentions_input_change(user_text):
        merged_ui_ctx["input_source"] = prev_input

    llm_result["ui_context"] = merged_ui_ctx

    if active_missing_field == "file_intake" and _is_upload_later_response(user_text):
        merged_ui_ctx["file_uploaded"] = False
        merged_ui_ctx["upload_deferred"] = True
        merged_ui_ctx["file_validation_status"] = "pending"
        llm_result["ui_context"] = merged_ui_ctx
        llm_result["missing_fields"] = [
            field for field in (llm_result.get("missing_fields") or [])
            if field != "file_intake"
        ]

    reply = llm_result.get("reply") or "No pude generar respuesta."

    meta_understood = bool(llm_result.get("meta_understood", False))
    needs_confirmation = bool(llm_result.get("needs_confirmation", False))
    user_confirmed = _is_user_confirming(user_text)
    user_declined = _is_user_declining(user_text)

    previous_confirmation_state = str(last_assistant_meta.get("confirmation_state") or "none")
    confirmation_state = previous_confirmation_state

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

    attempted_input = current_ui_ctx.get("input_source")
    attempted_output = current_ui_ctx.get("output_format")

    normalized_attempted_input = _normalize_input_source(attempted_input)
    if attempted_input is not None and normalized_attempted_input is None:
        canonical_missing.add("input_source")

    if attempted_output is not None and _normalize_output_format(attempted_output) is None:
        canonical_missing.add("output_format")


    # --- GUARDRAIL por ui_context (pero SIN romper el orden del flujo) ---
    ui_ctx = merged_ui_ctx

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

        doc_ok = doc and doc not in {"documento", "contrato", "archivo", "texto"}
        ag_ok = ag and ag not in {"analizar", "revisar", "ver"}

        if doc_ok and ag_ok:
            if not _has(ui_ctx.get("input_source")):
                canonical_missing.add("input_source")

            input_source = _normalize_input_source(ui_ctx.get("input_source"))
            file_uploaded = ui_ctx.get("file_uploaded") is True

            upload_deferred = ui_ctx.get("upload_deferred") is True

            if input_source == "local_upload" and not file_uploaded and not upload_deferred:
                canonical_missing.add("file_intake")

            result_type = _normalize_result_type(ui_ctx.get("result_type"))
            if not result_type:
                canonical_missing.add("result_type")

    llm_result["missing_fields"] = sorted(canonical_missing)

    # --- GUARDRAIL: no permitir confirmación si falta algo ---
    if llm_result["missing_fields"]:
        llm_result["needs_confirmation"] = False
        needs_confirmation = False

    # --- ANCLAR el flujo al campo pendiente activo ---
    # Solo mantenemos anclado el campo si TODAVÍA sigue faltando.
    active_input_missing = not _has(merged_ui_ctx.get("input_source"))
    active_file_intake_missing = (
        _normalize_input_source(merged_ui_ctx.get("input_source")) == "local_upload"
        and merged_ui_ctx.get("file_uploaded") is not True
    )
    active_result_type_missing = not _normalize_result_type(merged_ui_ctx.get("result_type"))
    active_output_missing = not _has(merged_ui_ctx.get("output_format"))

    if active_missing_field == "output_format" and active_output_missing:
        llm_result["missing_fields"] = ["output_format"]
        llm_result["needs_confirmation"] = False
        needs_confirmation = False

    elif active_missing_field == "file_intake" and active_file_intake_missing:
        llm_result["missing_fields"] = ["file_intake"]
        llm_result["needs_confirmation"] = False
        needs_confirmation = False

    elif active_missing_field == "input_source" and active_input_missing:
        llm_result["missing_fields"] = ["input_source"]
        llm_result["needs_confirmation"] = False
        needs_confirmation = False

    elif active_missing_field == "result_type" and active_result_type_missing:
        llm_result["missing_fields"] = ["result_type"]
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
    focus_asked = focus_asked_once

    # Si ya tenemos doc+analysis OK y todavía no se preguntó enfoque,
    # este turno SOLO pregunta focus (y NO deja pasar a input/output).
    if (
        meta_understood
        and doc_ok
        and ag_ok
        and not focus_asked
        and active_missing_field not in {"input_source", "result_type", "output_format"}
    ):
        llm_result["needs_confirmation"] = False
        needs_confirmation = False

        llm_result["missing_fields"] = ["focus"]  # <- SOLO focus, nada más
        llm_result["reply"] = "¿Hay algún énfasis adicional que quieras agregar?"
        reply = llm_result["reply"]

    missing_norm = set(llm_result.get("missing_fields") or [])

    # Reply coherente con el paso actual
    if "focus" in missing_norm:
        llm_result["reply"] = "¿Hay algún énfasis adicional que quieras agregar?"
    elif "input_source" in missing_norm:
        llm_result["reply"] = "¿Cómo vas a enviar o cargar el documento?"
    elif "file_intake" in missing_norm:
        llm_result["reply"] = "Sube tu archivo aquí."
    elif "result_type" in missing_norm:
        llm_result["reply"] = "¿Qué tipo de resultado esperas?"
    elif "output_format" in missing_norm:
        llm_result["reply"] = "¿En qué formato quieres el resultado?"

    reply = llm_result.get("reply") or reply

    # helper norm para condiciones posteriores
    missing_fields = llm_result.get("missing_fields") or []
    if not isinstance(missing_fields, list):
        missing_fields = []
    missing_fields_norm = [str(x).strip() for x in missing_fields if str(x).strip()]

    # Reconciliación final de faltantes usando el contexto ya fusionado y congelado.
    # Esto evita loops como input -> confirmación -> input.
    reconciled_missing: list[str] = []

    if not _has(merged_ui_ctx.get("document_type")):
        reconciled_missing.append("document_type")

    if not _has(merged_ui_ctx.get("analysis_goal")):
        reconciled_missing.append("analysis_goal")

    if not _has(merged_ui_ctx.get("input_source")):
        reconciled_missing.append("input_source")

    if (
        _normalize_input_source(merged_ui_ctx.get("input_source")) == "local_upload"
        and merged_ui_ctx.get("file_uploaded") is not True
        and merged_ui_ctx.get("upload_deferred") is not True
    ):
        reconciled_missing.append("file_intake")

    if not _normalize_result_type(merged_ui_ctx.get("result_type")):
        reconciled_missing.append("result_type")

    # focus solo falta si explícitamente el flujo actual lo está pidiendo
    if "focus" in missing_fields_norm:
        reconciled_missing.append("focus")

    missing_fields_norm = reconciled_missing
    llm_result["missing_fields"] = missing_fields_norm

    if missing_fields_norm:
        llm_result["needs_confirmation"] = False
        needs_confirmation = False
    elif meta_understood and confirmation_state != "editing":
        llm_result["needs_confirmation"] = True
        needs_confirmation = True

    # Si el paso activo previo era focus, lo cerramos con esta respuesta:
    # tanto si dijo "no" como si agregó un énfasis válido.
    if active_missing_field == "focus":
        llm_result["ui_context"] = merged_ui_ctx
        user_declined = False
        focus_asked_once = True

        next_missing: list[str] = []

        if not _has(merged_ui_ctx.get("input_source")):
            next_missing.append("input_source")

        if not _normalize_result_type(merged_ui_ctx.get("result_type")):
            next_missing.append("result_type")

        llm_result["missing_fields"] = next_missing
        missing_fields_norm = next_missing

        if next_missing:
            llm_result["needs_confirmation"] = False
            needs_confirmation = False
        else:
            llm_result["needs_confirmation"] = bool(meta_understood)
            needs_confirmation = bool(meta_understood)

        llm_result["reply"] = ""

    # Si el usuario niega o corrige, entramos en modo edición real.
    # No reabrimos automáticamente el flujo ni pedimos campos viejos aquí.
    if user_declined and not _is_focus_none_response(user_text):
        llm_result["needs_confirmation"] = False
        needs_confirmation = False
        user_confirmed = False
        confirmation_state = "editing"
        llm_result["missing_fields"] = []
        missing_fields_norm = []
        reply = "¿Qué quieres corregir o completar?"
        llm_result["reply"] = reply

    # Confirmación positiva real: solo si no falta nada
    elif user_confirmed and meta_understood and not missing_fields_norm:
        llm_result["needs_confirmation"] = False
        needs_confirmation = False
        confirmation_state = "none"

        reply = "Listo. Ruta confirmada."
        llm_result["reply"] = reply
        llm_result["understanding_steps"] = []

    # Si ya estábamos en edición y el usuario dio una corrección concreta,
    # salimos de editing y recalculamos si toca volver a confirmación o pedir algo faltante.
    elif previous_confirmation_state == "editing":
        confirmation_state = "none"
        user_confirmed = False
        user_declined = False

        next_missing: list[str] = []

        if not _has(merged_ui_ctx.get("document_type")):
            next_missing.append("document_type")

        if not _has(merged_ui_ctx.get("analysis_goal")):
            next_missing.append("analysis_goal")

        if not _has(merged_ui_ctx.get("input_source")):
            next_missing.append("input_source")

        if not _normalize_result_type(merged_ui_ctx.get("result_type")):
            next_missing.append("result_type")

        llm_result["missing_fields"] = next_missing
        missing_fields_norm = next_missing

        if next_missing:
            llm_result["needs_confirmation"] = False
            needs_confirmation = False
        else:
            llm_result["needs_confirmation"] = bool(meta_understood)
            needs_confirmation = bool(meta_understood)

        llm_result["reply"] = ""

    # Estado inicial del CTA/plan antes de calcular confirmación
    cta_ready = False
    plan_created = False
    plan_id = None
    plan_status = None

    if confirmation_state == "editing":
        active_step = "confirmation_edit"
        interaction_mode = "review_edit"
    else:
        if needs_confirmation:
            confirmation_state = "awaiting_confirmation"
        else:
            confirmation_state = "none"

        active_step = _resolve_active_step(
            missing_fields=missing_fields_norm,
            needs_confirmation=needs_confirmation,
            confirmation_state=confirmation_state,
        )

        interaction_mode = _resolve_interaction_mode(
            active_step=active_step,
            confirmation_state=confirmation_state,
        )

    # Alinear reply con el paso real del flujo.
    # Solo respetamos replies especiales de confirmación o edición;
    # para el resto, manda el active_step real.
    current_reply = (llm_result.get("reply") or "").strip()

    special_replies = {
        "Listo. Ruta confirmada.",
        "Ruta confirmada.",
        "¿Qué quieres corregir o completar?",
    }

    if current_reply in special_replies:
        reply = current_reply
    else:
        reply = _reply_for_active_step(active_step, confirmation_state)
        llm_result["reply"] = reply

    # Si todavía falta algo, el reply debe corresponder al active_step faltante
    # y no a una confirmación vieja.
    if missing_fields_norm and active_step != "confirmation_edit":
        reply = _reply_for_active_step(active_step, confirmation_state)
        llm_result["reply"] = reply

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

    # Confirmación positiva real: si no falta nada, no reabrimos fases previas.
    if user_confirmed and meta_understood and not missing_fields_norm:
        llm_result["needs_confirmation"] = False
        needs_confirmation = False
        confirmation_state = "none"

    if user_confirmed and meta_understood and not missing_fields_norm and not user_declined:
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

    # Recalcular active_step / interaction_mode con el estado final real del turno
    if confirmation_state == "editing":
        active_step = "confirmation_edit"
        interaction_mode = "review_edit"
    elif cta_ready:
        active_step = "confirmation"
        interaction_mode = "free_text"
    else:
        active_step = _resolve_active_step(
            missing_fields=missing_fields_norm,
            needs_confirmation=needs_confirmation,
            confirmation_state=confirmation_state,
        )
        interaction_mode = _resolve_interaction_mode(
            active_step=active_step,
            confirmation_state=confirmation_state,
        )

    # 6) UI Hints (botones)
    ui_hints = _build_ui_hints(
        active_step=active_step,
        needs_confirmation=needs_confirmation,
        cta_ready=cta_ready,
    )

    # 7) UI Bullets (lista/timeline)
    ui_bullets = _build_ui_bullets(
        active_step=active_step,
        llm_result=llm_result,
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
        "active_step": active_step,
        "interaction_mode": interaction_mode,
        "confirmation_state": confirmation_state,
        "focus_asked_once": focus_asked_once,
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
        "active_step": active_step,
        "interaction_mode": interaction_mode,
        "confirmation_state": confirmation_state,
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