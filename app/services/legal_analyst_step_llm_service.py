import json
import re
from typing import Any, Dict

from app.core.openai_client import get_openai_client

MODEL = "gpt-4.1"


def _safe_get_output_text(response: Any) -> str:
    txt = getattr(response, "output_text", None)
    if isinstance(txt, str) and txt.strip():
        return txt.strip()

    try:
        chunks: list[str] = []
        for item in (getattr(response, "output", None) or []):
            for content in (getattr(item, "content", None) or []):
                text = getattr(content, "text", None)
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
        if chunks:
            return "\n".join(chunks).strip()
    except Exception:
        pass

    return ""


def _extract_json_object(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("Empty LLM output")

    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")

    return json.loads(match.group(0))


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _build_upload_block(step_id: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{step_id}_upload_again",
            "type": "file_uploader",
            "label": "Arrastra y suelta el archivo aquí, o súbelo desde tu equipo.",
            "accepted_formats": ["pdf", "docx", "txt"],
        }
    ]


def _is_gratitude_message(user_message: str) -> bool:
    normalized = _normalize_text(user_message)

    gratitude_patterns = {
        "gracias",
        "muchas gracias",
        "ok gracias",
        "vale gracias",
        "perfecto gracias",
        "listo gracias",
        "entendido gracias",
        "genial gracias",
        "ok",
        "vale",
        "perfecto",
        "entendido",
        "listo",
        "bien",
    }

    return normalized in gratitude_patterns


def _should_force_upload_block(step_id: str, user_message: str) -> bool:
    if step_id != "load_contract":
        return False

    normalized = _normalize_text(user_message)

    trigger_phrases = [
        "subir archivo",
        "subir mi archivo",
        "subir mi pdf",
        "subir pdf",
        "mostrar bloque",
        "mostrar el bloque",
        "muéstrame el bloque",
        "muestrame el bloque",
        "mostrar uploader",
        "vuelve a mostrar",
        "volver a mostrar",
        "dame el bloque",
        "dame de nuevo el bloque",
        "bloque para subir",
        "puedo subir mi archivo",
        "quiero subir mi archivo",
        "necesito subir mi archivo",
        "necesito subir mi pdf",
        "vuelve a mostrar el bloque para subir",
        "muéstrame otra vez el bloque",
        "muestrame otra vez el bloque",
    ]

    return any(phrase in normalized for phrase in trigger_phrases)


def _build_system_prompt(step_id: str) -> str:
    if step_id == "load_contract":
        return """
Eres el mini asistente del Analista Legal de Minka, dentro del paso "Leer contrato".

Tu rol:
- Responder SOLO sobre este paso.
- Este paso trata únicamente sobre carga y validación inicial del documento.
- El usuario puede preguntar sobre:
  - formatos permitidos
  - si puede subir PDF, DOCX o TXT
  - cómo cargar el archivo
  - qué ocurre en este paso
  - si necesita subir el contrato antes de continuar
  - si quiere que vuelvas a mostrar el bloque para subir archivo

No debes responder sobre:
- riesgos del contrato
- hallazgos legales
- cláusulas críticas
- priorización de riesgos
- interpretación práctica
- exportaciones finales

Si el usuario pide volver a mostrar el bloque o uploader:
- responde afirmativamente
- devuelve render_blocks con un file_uploader

Si el usuario agradece o solo cierra la interacción:
- responde de forma breve y cordial
- NO devuelvas render_blocks

Si el usuario pregunta algo fuera del scope:
- responde breve
- redirígelo diciendo que eso se analiza en los siguientes pasos
- no inventes resultados legales

Reglas de estilo:
- responde en español
- respuestas cortas y claras
- máximo 2 frases
- tono profesional y útil
- no uses markdown
- no enumeres demasiado

Responde SOLO JSON válido:
{
  "reply": "texto breve",
  "render_blocks": [
    {
      "id": "string",
      "type": "file_uploader",
      "label": "string",
      "accepted_formats": ["pdf", "docx", "txt"]
    }
  ]
}

Si no necesitas mostrar ningún bloque, devuelve:
{
  "reply": "texto breve",
  "render_blocks": []
}
        """.strip()

    return """
Eres el mini asistente de un paso del Analista Legal de Minka.

Responde SOLO sobre el paso actual, sin salirte del contexto.
Responde en español, breve y claro.

Responde SOLO JSON válido:
{
  "reply": "texto breve",
  "render_blocks": []
}
    """.strip()


def call_legal_step_llm(
    *,
    step_id: str,
    user_message: str,
    goal_type: str | None = None,
    document_id: str | None = None,
    filename: str | None = None,
    step_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if _is_gratitude_message(user_message):
        return {
            "reply": "Con gusto. Cuando quieras, puedes subir el contrato para continuar.",
            "render_blocks": [],
        }

    if _should_force_upload_block(step_id, user_message):
        return {
            "reply": "Claro, aquí tienes nuevamente el bloque para subir tu archivo.",
            "render_blocks": _build_upload_block(step_id),
        }

    client = get_openai_client()

    prompt_context = {
        "step_id": step_id,
        "goal_type": goal_type,
        "document_id": document_id,
        "filename": filename,
        "step_output": step_output or {},
        "user_message": user_message,
    }

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": _build_system_prompt(step_id)},
            {
                "role": "user",
                "content": (
                    "Contexto del paso:\n"
                    f"{json.dumps(prompt_context, ensure_ascii=False)}\n\n"
                    "Responde SOLO con JSON válido."
                ),
            },
        ],
        temperature=0.2,
        max_output_tokens=220,
    )

    raw_output = _safe_get_output_text(response)

    try:
        parsed = _extract_json_object(raw_output)

        reply = parsed.get("reply")
        render_blocks = parsed.get("render_blocks", [])

        if not isinstance(reply, str) or not reply.strip():
            reply = "En este paso solo te ayudo a cargar y validar el contrato antes de continuar."

        if not isinstance(render_blocks, list):
            render_blocks = []

        normalized_blocks: list[dict[str, Any]] = []
        for block in render_blocks:
            if not isinstance(block, dict):
                continue

            block_type = str(block.get("type", "")).strip()
            if block_type != "file_uploader":
                continue

            accepted_formats = block.get("accepted_formats", [])
            if not isinstance(accepted_formats, list):
                accepted_formats = []

            normalized_blocks.append(
                {
                    "id": str(block.get("id") or f"{step_id}_upload_again"),
                    "type": "file_uploader",
                    "label": str(
                        block.get("label")
                        or "Arrastra y suelta el archivo aquí, o súbelo desde tu equipo."
                    ),
                    "accepted_formats": [
                        str(x).strip().lower()
                        for x in accepted_formats
                        if str(x).strip()
                    ] or ["pdf", "docx", "txt"],
                }
            )

        return {
            "reply": reply.strip(),
            "render_blocks": normalized_blocks,
        }
    except Exception:
        pass

    return {
        "reply": "En este paso solo te ayudo a cargar y validar el contrato antes de continuar.",
        "render_blocks": [],
    }