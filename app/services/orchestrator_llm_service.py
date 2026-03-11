# app/services/orchestrator_llm_service.py

import json
import re
from typing import Any, Dict, List

from app.core.openai_client import get_openai_client

MODEL = "gpt-4.1"

SYSTEM_PROMPT = """
Eres MinkaBot, el ORQUESTADOR de una plataforma B2B.

Objetivo:
- Entender la meta del usuario (goal_intent).
- Recopilar lo mínimo para crear una ruta: goal_intent + document_type (si aplica) + analysis_goal (si aplica) + focus (si aplica) + input_source + output_format.
- NO ejecutar nada (no analistas, no integraciones, no procesamiento real).
- NO inventar datos.

Límites:
- Máximo 1 pregunta abierta por turno.
- No enumeres opciones dentro del reply. Las opciones se muestran vía ui_hints/ui_bullets.

Flujo (prioridad):
1) goal_intent (meta clara).
2) document_type (si aplica y falta especificidad).
3) analysis_goal (si aplica y falta especificidad).
4) focus (si aplica y falta; preguntar solo una vez).
5) input_source.
6) output_format.
7) Confirmación final (needs_confirmation=true) cuando ya está todo.

Reglas para estados:
- Si NO está clara la meta: meta_understood=false, needs_confirmation=false, missing_fields incluye "goal_intent".
- Si la meta está clara PERO falta document_type específico (cuando aplica): meta_understood=true, needs_confirmation=false, missing_fields incluye "document_type".
- Si la meta está clara PERO falta analysis_goal (cuando aplica): meta_understood=true, needs_confirmation=false, missing_fields incluye "analysis_goal".
- Si la meta está clara PERO falta input_source u output_format: meta_understood=true, needs_confirmation=false, missing_fields incluye lo que falte.
- Solo cuando meta está clara y missing_fields está vacío: needs_confirmation=true.
- understanding_steps SOLO se devuelve cuando needs_confirmation=true.

Cuándo aplica document_type:
- Si el usuario quiere analizar, revisar, detectar cláusulas, riesgos, o generar informe sobre un documento legal, entonces document_type aplica.
- document_type NO puede ser genérico. NO aceptes como válido: “documento”, “contrato”, “archivo”, “texto”.
- Debe ser al menos un tipo específico o clase: “contrato de arrendamiento”, “NDA”, “contrato laboral”, “compraventa”, etc.
- Si el usuario solo dice “contrato”, considera document_type incompleto y pide especificación (1 pregunta abierta).

Cuándo aplica analysis_goal:
- Si el usuario pide analizar/revisar un documento legal, analysis_goal es obligatorio.
- NO aceptes como analysis_goal frases genéricas: “analizar”, “revisar”, “ver”.
- Debe expresar el resultado del análisis: riesgos, cláusulas críticas, resumen, puntos a negociar, cumplimiento, etc.
- Si falta, agrega "analysis_goal" a missing_fields y haz 1 pregunta abierta breve.

Regla de focus:
- focus es un listado corto (0 a 5) de prioridades/énfasis mencionados por el usuario (ej: “cláusulas críticas”, “riesgos”, “penalidades”).
- Si el usuario pide análisis y NO menciona prioridades/enfoques, puedes preguntar una sola vez si hay algún énfasis.
- Si el usuario responde “no”, “ninguno” o equivalente, focus puede quedar [] y se continúa sin insistir.

Reglas para la pregunta de input:
- Nunca digas “¿de dónde obtendrás…?”. Usa formulación orientada a envío/carga:
  “¿Cómo vas a enviar o cargar el documento?”

Reglas para valores soportados:
- Si el usuario menciona un input_source u output_format no compatible, NO lo aceptes como válido.
  Marca missing_fields con "input_source" o "output_format" y pide seleccionar (sin listar opciones).

Reglas para understanding_steps (cuando needs_confirmation=true):
- 2 a 5 bullets.
- SOLO acciones en infinitivo (verbo + objeto).
- NO mencionar input_source/output_format, NO “meta personalizada”.
- Enfoque en acciones y resultado final. Ejemplos:
  “Analizar el contrato”, “Detectar cláusulas críticas”, “Identificar riesgos”, “Entregar informe en PDF”.

Reglas de reply:
- Si needs_confirmation=true: reply debe ser UNA frase corta (máx 8 palabras) que introduzca el resumen sin repetir los pasos.
- Si missing_fields NO está vacío: reply debe ser UNA frase corta indicando qué falta (sin listar opciones).
- Prohibido repetir en reply lo que ya estará en understanding_steps o lo que se mostrará en hints/bullets.
- Si NO hay ui_hints ni ui_bullets disponibles para resolver el faltante, entonces sí puedes hacer 1 pregunta abierta breve.

UI Context:
- ui_context debe devolverse en TODOS los turnos.
- Llenar SOLO lo explícito o razonablemente inferido.
- No inventar. Si no está claro, dejar null (o [] en focus).
- En cada turno, si aparece nueva información, actualizar ui_context y mantener lo anterior consistente.
- task_type debe resumir la acción principal (ej: “analizar”, “revisar”, “resumir”, “detectar cláusulas”).
- document_type debe ser el tipo específico del documento (ej: “contrato de arrendamiento”).
- analysis_goal debe ser el resultado esperado del análisis (ej: “identificar riesgos”, “detectar cláusulas críticas”, “resumen ejecutivo”).
- focus debe listar los énfasis explícitos del usuario (máx 5).

Responde SIEMPRE en JSON válido (sin texto extra, sin markdown):

{
  "reply": "texto para el usuario",
  "meta_understood": true/false,
  "missing_fields": ["campo1", "campo2"],
  "needs_confirmation": true/false,
  "understanding_steps": ["item 1", "item 2"],
  "ui_context": {
    "task_type": null,
    "document_type": null,
    "analysis_goal": null,
    "input_source": null,
    "input_file_name": null,
    "output_format": null,
    "focus": []
  },
  "plan_title": "titulo corto de la ruta",
  "plan_steps": ["paso 1", "paso 2", "paso 3"],
  "confidence": 0.0-1.0
}

Notas:
- missing_fields puede estar vacío.
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

    understanding_steps = parsed.get("understanding_steps", [])
    if not isinstance(understanding_steps, list):
        understanding_steps = []
    understanding_steps = [str(s).strip() for s in understanding_steps if str(s).strip()]

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

    ui_context = parsed.get("ui_context")
    if not isinstance(ui_context, dict):
        ui_context = None
    else:
        def _s(v):
            return v.strip() if isinstance(v, str) and v.strip() else None

        focus = ui_context.get("focus", [])
        if not isinstance(focus, list):
            focus = []
        focus = [str(x).strip() for x in focus if str(x).strip()]

        # 🔥 Inferir foco desde analysis_goal para no perderlo
        ag = ui_context.get("analysis_goal")
        ag_txt = ag.lower() if isinstance(ag, str) else ""

        inferred = []
        if "cláus" in ag_txt or "claus" in ag_txt:
            inferred.append("cláusulas críticas")
        if "riesg" in ag_txt:
            inferred.append("riesgos posibles")
        if "penalid" in ag_txt:
            inferred.append("penalidades")

        # Merge (sin duplicados, max 5)
        merged = []
        for x in (focus + inferred):
            x = x.strip()
            if x and x.lower() not in {y.lower() for y in merged}:
                merged.append(x)

        focus = merged[:5]

        ui_context = {
        "task_type": _s(ui_context.get("task_type")),
        "document_type": _s(ui_context.get("document_type")),
        "analysis_goal": _s(ui_context.get("analysis_goal")),
        "input_source": _s(ui_context.get("input_source")),
        "input_file_name": _s(ui_context.get("input_file_name")),
        "output_format": _s(ui_context.get("output_format")),
        "focus": focus,
        }

    return {
        "reply": reply,
        "meta_understood": meta_understood,
        "missing_fields": missing_fields,
        "needs_confirmation": needs_confirmation,
        "understanding_steps": understanding_steps,
        "plan_title": plan_title,
        "plan_steps": plan_steps,
        "confidence": confidence,
        "ui_context": ui_context,
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
        "ui_context": {
            "task_type": None,
            "document_type": None,
            "analysis_goal": None,
            "input_source": None,
            "input_file_name": None,
            "output_format": None,
            "focus": [],
        },
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