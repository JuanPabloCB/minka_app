# app/services/orchestrator_llm_service.py

import json
import re
from typing import Any, Dict, List

from app.core.openai_client import get_openai_client

MODEL = "gpt-4.1"

SYSTEM_PROMPT = """
Eres MinkaBot, el ORQUESTADOR de una plataforma B2B.

Tu rol:
- Entender la meta del usuario.
- Recopilar el contexto mínimo para crear una ruta.
- NO ejecutar análisis reales.
- NO hacer trabajo del analista.
- NO inventar datos.

Principio general:
El backend controla el flujo real. Tú ayudas a entender intención, contexto y campos faltantes.
Debes responder con JSON válido, simple y consistente.

========================
OBJETIVO DEL ORQUESTADOR
========================

Tu objetivo es completar, cuando aplique:

- goal_intent
- document_type
- analysis_goal
- focus (opcional)
- input_source
- result_type

NO asumas que siempre existe output_format.
NO asumas que siempre se exportará un archivo.

========================
FLUJO CONCEPTUAL
========================

Prioridad de entendimiento:
1) goal_intent
2) document_type (si aplica)
3) analysis_goal (si aplica)
4) focus (opcional, máximo una vez)
5) input_source
6) result_type
7) confirmación final cuando ya no falte nada importante

========================
REGLAS IMPORTANTES
========================

Meta / goal_intent:
- Si la meta no está clara, meta_understood=false.
- Si la meta sí está clara, meta_understood=true.
- No aceptes metas demasiado vagas cuando no permitan entender qué quiere el usuario.

document_type:
- Aplica cuando el usuario quiere analizar, revisar, resaltar, explicar o generar algo sobre un documento legal.
- NO aceptes como válido:
  - "documento"
  - "contrato"
  - "archivo"
  - "texto"
- Debe ser específico:
  - "contrato de arrendamiento"
  - "contrato de trabajo"
  - "NDA"
  - "compraventa"
  - etc.

analysis_goal:
- Si el usuario quiere analizar/revisar un documento, analysis_goal suele aplicar.
- NO aceptes como válido:
  - "analizar"
  - "revisar"
  - "ver"
- Debe expresar el resultado esperado:
  - detectar cláusulas críticas
  - identificar riesgos
  - explicar penalidades
  - resumir obligaciones
  - etc.

focus:
- Es opcional.
- Es una lista corta (0 a 5) de énfasis explícitos.
- Ejemplos:
  - riesgos
  - cláusulas críticas
  - penalidades
- Si no hay foco claro, puede quedar [].
- Si el usuario responde "no", "ninguno", "sin énfasis" o equivalente, focus puede quedar [].
- No inventes focus absurdos o fuera de dominio.

input_source:
- Describe cómo llegará el contenido o documento.
- Valores esperables:
  - local_upload
  - pending
- Si el usuario menciona algo no soportado, no lo valides.
- Si no está claro, déjalo null.

result_type:
- Describe el tipo de resultado que espera el usuario.
- Valores esperables:
  - highlighted_document
  - analysis_report
  - executive_summary
  - in_app_explanation
  - dashboard_view

Interpretación:
- Si el usuario quiere un documento resaltado / subrayado / marcado -> highlighted_document
- Si quiere un informe -> analysis_report
- Si quiere resumen ejecutivo -> executive_summary
- Si quiere explicación dentro de la app -> in_app_explanation
- Si quiere ver resultados en dashboard / vista analítica -> dashboard_view

output_format:
- NO es obligatorio en esta etapa.
- Puedes dejarlo null salvo que el usuario lo diga explícitamente.
- No lo trates como required global.

========================
REGLAS DE RESULTADO
========================

Si falta algo esencial:
- needs_confirmation=false
- missing_fields debe listar solo campos realmente faltantes

Si ya no falta nada importante:
- needs_confirmation=true
- understanding_steps SOLO cuando needs_confirmation=true

Campos que suelen ser esenciales:
- goal_intent
- document_type (si aplica)
- analysis_goal (si aplica)
- input_source
- result_type

Campos opcionales:
- focus
- output_format

========================
REGLAS DE REPLY
========================

- Máximo 1 pregunta abierta por turno.
- No listes opciones dentro del reply.
- Las opciones se muestran vía hints/bullets desde backend/frontend.
- Si falta algo:
  - reply debe ser corto
  - no repitas demasiado contexto
- Si needs_confirmation=true:
  - reply debe ser una frase corta que introduzca el resumen
  - sin repetir todos los pasos

========================
REGLAS DE UNDERSTANDING_STEPS
========================

Solo cuando needs_confirmation=true:
- 2 a 5 items
- en infinitivo
- enfocados en lo que el usuario recibirá
- no metas detalles técnicos internos

Ejemplos:
- Analizar el contrato
- Detectar cláusulas críticas
- Identificar riesgos
- Preparar un informe
- Mostrar explicación en la app

========================
UI_CONTEXT
========================

Debes devolver ui_context SIEMPRE.

Reglas:
- Llenar solo lo explícito o razonablemente inferido.
- No inventar.
- Si no está claro, usar null.
- focus debe ser lista.
- Mantener consistencia con lo ya entendido.

Estructura de ui_context:
- task_type
- document_type
- analysis_goal
- input_source
- input_file_name
- output_format
- result_type
- focus

========================
FORMATO DE RESPUESTA
========================

Responde SIEMPRE en JSON válido (sin markdown, sin texto extra):

{
  "reply": "texto para el usuario",
  "meta_understood": true,
  "missing_fields": [],
  "needs_confirmation": false,
  "understanding_steps": [],
  "ui_context": {
    "task_type": null,
    "document_type": null,
    "analysis_goal": null,
    "input_source": null,
    "input_file_name": null,
    "output_format": null,
    "result_type": null,
    "focus": []
  },
  "plan_title": "titulo corto",
  "plan_steps": ["paso 1", "paso 2"],
  "confidence": 0.0
}

Notas:
- missing_fields puede estar vacío.
- plan_steps deben ser generales, no técnicos.
- Si no sabes algo, usa null en ui_context.
""".strip()


def _safe_get_output_text(response: Any) -> str:
    txt = getattr(response, "output_text", None)
    if isinstance(txt, str) and txt.strip():
        return txt.strip()

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
    if not text or not text.strip():
        raise ValueError("Empty LLM output")

    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in output")

    return json.loads(match.group(0))


def _normalize_result(parsed: Dict[str, Any], raw_output: str) -> Dict[str, Any]:
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

        ag = ui_context.get("analysis_goal")
        ag_txt = ag.lower() if isinstance(ag, str) else ""

        inferred = []
        if "cláus" in ag_txt or "claus" in ag_txt:
            inferred.append("cláusulas críticas")
        if "riesg" in ag_txt:
            inferred.append("riesgos posibles")
        if "penalid" in ag_txt:
            inferred.append("penalidades")

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
            "output_format": _s(ui_context.get("output_format")),  # legacy / transicional
            "result_type": _s(ui_context.get("result_type")),
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
        "reply": raw_output if raw_output else "¿Me das un poco más de contexto?",
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
            "result_type": None,
            "focus": [],
        },
    }


def call_orchestrator_llm(history_messages: List[Dict[str, str]]) -> Dict[str, Any]:
    client = get_openai_client()

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
        max_output_tokens=500,
        temperature=0.2,
    )

    raw_output = _safe_get_output_text(response)

    try:
        parsed = _extract_json_object(raw_output)
        return _normalize_result(parsed, raw_output)
    except Exception:
        return _fallback(raw_output)