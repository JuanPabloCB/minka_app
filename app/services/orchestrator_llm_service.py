import json
import re
from typing import Any, Dict, List

from app.core.openai_client import client

MODEL = "gpt-4.1"

SYSTEM_PROMPT = """
Eres MinkaBot, el Orquestador de una plataforma B2B.

Tu función:
- Entender la meta del usuario.
- Hacer máximo 1 o 2 preguntas estratégicas por turno.
- NO ejecutar nada.
- NO crear planes.
- NO asumir información que no fue dada.
- Ser preciso.
- Activar CTA solo cuando tengas mínimo contexto suficiente.

Debes responder SIEMPRE en formato JSON válido con esta estructura (sin texto extra, sin markdown):

{
  "reply": "texto que verá el usuario",
  "meta_understood": true/false,
  "missing_fields": ["campo1", "campo2"],
  "confidence": 0.0-1.0
}
"""


def _safe_get_output_text(response: Any) -> str:
    """
    Intenta extraer el texto del SDK Responses sin depender de un solo atributo.
    """
    # 1) Lo "bonito" si existe
    if hasattr(response, "output_text") and isinstance(response.output_text, str) and response.output_text.strip():
        return response.output_text.strip()

    # 2) Fallback: recorrer response.output (estructura típica)
    try:
        chunks = []
        for item in getattr(response, "output", []) or []:
            for c in getattr(item, "content", []) or []:
                # text content suele venir como {type:"output_text", text:"..."}
                text = getattr(c, "text", None)
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
        if chunks:
            return "\n".join(chunks).strip()
    except Exception:
        pass

    # 3) Último recurso
    return ""


def _extract_json_object(text: str) -> Dict[str, Any]:
    """
    Extrae el primer objeto JSON del texto, incluso si viene con ```json ... ```.
    """
    if not text:
        raise ValueError("Empty LLM output")

    # Quitar fences tipo ```json ... ```
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    # Si ya es JSON puro
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    # Buscar el primer bloque {...} (greedy controlado)
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in output")

    return json.loads(match.group(0))


def _normalize_result(parsed: Dict[str, Any], raw_output: str) -> Dict[str, Any]:
    """
    Asegura claves y tipos esperados.
    """
    reply = parsed.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        reply = raw_output.strip() if isinstance(raw_output, str) and raw_output.strip() else "¿Me das un poco más de contexto?"

    meta_understood = parsed.get("meta_understood", False)
    meta_understood = bool(meta_understood)

    missing_fields = parsed.get("missing_fields", [])
    if not isinstance(missing_fields, list):
        missing_fields = []

    confidence = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    # clamp 0..1
    if confidence < 0.0:
        confidence = 0.0
    if confidence > 1.0:
        confidence = 1.0

    return {
        "reply": reply,
        "meta_understood": meta_understood,
        "missing_fields": missing_fields,
        "confidence": confidence,
    }


def call_orchestrator_llm(user_messages: List[str]) -> Dict[str, Any]:
    conversation_text = "\n".join(user_messages)

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Conversación completa hasta ahora:\n"
                    f"{conversation_text}\n\n"
                    "Responde SOLO con el JSON (sin markdown)."
                ),
            },
        ],
        max_output_tokens=400,
        temperature=0.2,
    )

    raw_output = _safe_get_output_text(response)

    try:
        parsed = _extract_json_object(raw_output)
        return _normalize_result(parsed, raw_output)
    except Exception:
        # fallback seguro
        fallback = {
            "reply": raw_output.strip() if raw_output.strip() else (
                "Para ayudarte bien, dime: (1) ¿Cuál es tu meta exacta? "
                "(2) ¿Qué resultado final esperas? (3) ¿Hay alguna restricción importante?"
            ),
            "meta_understood": False,
            "missing_fields": [],
            "confidence": 0.3,
        }
        return fallback