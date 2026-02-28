# app/services/orchestrator_llm_service.py

import json
import re
from typing import Any, Dict, List

from app.core.openai_client import get_openai_client

MODEL = "gpt-4.1"

SYSTEM_PROMPT = """
Eres MinkaBot, el Orquestador de una plataforma B2B.

Tu función:
- Entender la meta del usuario.
- Hacer máximo 1 o 2 preguntas estratégicas por turno.
- NO ejecutar nada (no analistas, no Gmail, no Excel).
- NO inventar datos.
- Ser preciso y directo.
- Activar CTA solo cuando tengas contexto suficiente Y el usuario haya confirmado.

Regla clave (MVP):
- Si ya entiendes la meta, primero pide confirmación final con un resumen.
- Solo después de que el usuario confirme, ya NO pidas más preguntas y deja lista la ruta.

Responde SIEMPRE en JSON válido con esta estructura (sin texto extra, sin markdown):

{
  "reply": "texto para el usuario",
  "meta_understood": true/false,
  "missing_fields": ["campo1", "campo2"],
  "needs_confirmation": true/false,
  "plan_title": "titulo corto de la ruta",
  "plan_steps": ["paso 1", "paso 2", "paso 3"],
  "confidence": 0.0-1.0
}

Notas:
- missing_fields puede estar vacío.
- needs_confirmation = true cuando ya entiendes pero falta el “¿confirmas que esto es todo?”
- plan_steps deben ser GENERALES (tipo 5-7 pasos), no acciones técnicas.
""".strip()


def _safe_get_output_text(response: Any) -> str:
    """
    Extrae texto del Responses API sin depender de un único atributo.
    """
    # 1) Atributo directo si existe
    txt = getattr(response, "output_text", None)
    if isinstance(txt, str) and txt.strip():
        return txt.strip()

    # 2) Recorrer estructura response.output -> content -> text
    try:
        chunks: List[str] = []
        for item in (getattr(response, "output", None) or []):
            for c in (getattr(item, "content", None) or []):
                text = getattr(c, "text", None)
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
        if chunks:
            return "\n".join(chunks).strip()
    except Exception:
        pass

    return ""


def _extract_json_object(text: str) -> Dict[str, Any]:
    """
    Extrae el primer objeto JSON del texto.
    Maneja fences ```json ... ``` y casos con texto antes/después.
    """
    if not text or not text.strip():
        raise ValueError("Empty LLM output")

    text = text.strip()

    # quitar fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    # caso: JSON puro
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    # buscar primer bloque { ... }
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in output")

    return json.loads(match.group(0))


def _normalize_result(parsed: Dict[str, Any], raw_output: str) -> Dict[str, Any]:
    """
    Normaliza tipos, aplica defaults y asegura el contrato.
    """
    reply = parsed.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        reply = raw_output.strip() if isinstance(raw_output, str) and raw_output.strip() else "¿Me das un poco más de contexto?"

    meta_understood = bool(parsed.get("meta_understood", False))

    missing_fields = parsed.get("missing_fields", [])
    if not isinstance(missing_fields, list):
        missing_fields = []
    missing_fields = [str(x).strip() for x in missing_fields if str(x).strip()]

    needs_confirmation = bool(parsed.get("needs_confirmation", False))

    plan_title = parsed.get("plan_title", "")
    if not isinstance(plan_title, str):
        plan_title = ""
    plan_title = plan_title.strip()

    plan_steps = parsed.get("plan_steps", [])
    if not isinstance(plan_steps, list):
        plan_steps = []
    plan_steps = [str(s).strip() for s in plan_steps if str(s).strip()]

    confidence = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return {
        "reply": reply,
        "meta_understood": meta_understood,
        "missing_fields": missing_fields,
        "needs_confirmation": needs_confirmation,
        "plan_title": plan_title,
        "plan_steps": plan_steps,
        "confidence": confidence,
    }


def _fallback(raw_output: str) -> Dict[str, Any]:
    raw_output = (raw_output or "").strip()

    return {
        "reply": raw_output if raw_output else (
            "Para ayudarte bien, dime: "
            "(1) ¿Cuál es tu meta exacta? "
            "(2) ¿Qué resultado final esperas? "
            "(3) ¿Hay alguna restricción importante?"
        ),
        "meta_understood": False,
        "missing_fields": [],
        "needs_confirmation": False,
        "plan_title": "",
        "plan_steps": [],
        "confidence": 0.3,
    }


def call_orchestrator_llm(history_messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    history_messages: lista de mensajes ya formateados tipo:
      [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}]

    Retorna dict normalizado con el contrato del orquestador.
    """
    client = get_openai_client()

    # defensivo: validar estructura mínima
    safe_history: List[Dict[str, str]] = []
    for m in history_messages or []:
        role = (m.get("role") or "").strip()
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            safe_history.append({"role": role, "content": content})

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *safe_history,
            {"role": "user", "content": "Responde SOLO con el JSON (sin markdown)."},
        ],
        max_output_tokens=400,
        temperature=0.2,
    )

    raw_output = _safe_get_output_text(response)

    try:
        parsed = _extract_json_object(raw_output)
        return _normalize_result(parsed, raw_output)
    except Exception:
        return _fallback(raw_output)