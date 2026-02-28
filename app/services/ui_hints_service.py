from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.orchestrator_turn import UIHint, UIHintOption, UIHintsOut


# Catálogo simple de “inputs/herramientas”
# (por ahora todo es UI; la conexión real OAuth vendrá después)
TOOLS = [
    {"key": "gmail", "label": "Gmail"},
    {"key": "google_drive", "label": "Google Drive"},
    {"key": "outlook", "label": "Outlook"},
    {"key": "dropbox", "label": "Dropbox"},
    {"key": "local_upload", "label": "Subir archivo"},
]


def build_ui_hints(*, llm_result: Dict[str, Any], cta_ready: bool, plan_id: Any) -> UIHintsOut:
    """
    Genera hints determinísticos para el frontend.
    NO depende del LLM para “inventar botones”.
    """
    hints: List[UIHint] = []

    needs_confirmation = bool(llm_result.get("needs_confirmation", False))
    missing_fields = llm_result.get("missing_fields") or []
    if not isinstance(missing_fields, list):
        missing_fields = []

    reply_text = (llm_result.get("reply") or "").lower()

    # 1) Si el orquestador está pidiendo confirmación final -> Sí/No
    if needs_confirmation:
        hints.append(
            UIHint(
                type="quick_replies",
                title="Confirmación",
                options=[
                    UIHintOption(key="yes", label="Sí", value="Sí, confirmo."),
                    UIHintOption(key="no", label="No", value="No, corrijo algo: "),
                ],
            )
        )

    # 2) Si el usuario aún no definió input o el bot preguntó por fuente de datos
    # Heurística: si reply menciona input / archivo / fuente / contratos / subir
    wants_input = any(
        kw in reply_text
        for kw in ["input", "archivo", "fuente", "drive", "gmail", "outlook", "sube", "subir", "contrato", "documento"]
    )
    wants_input = wants_input or ("input" in [str(x).lower() for x in missing_fields])

    if wants_input:
        hints.append(
            UIHint(
                type="tool_select",
                title="¿Qué input tienes por el momento?",
                options=[
                    UIHintOption(key=t["key"], label=t["label"], value=t["label"])
                    for t in TOOLS
                ],
                meta={"multi_select": True},
            )
        )

    # 3) Si ya está listo el CTA -> acciones para UI
    if cta_ready:
        options = [
            UIHintOption(key="view_plan", label="Ver ruta", value=str(plan_id) if plan_id else None),
            UIHintOption(key="start", label="Iniciar ejecución", value=str(plan_id) if plan_id else None),
        ]
        hints.append(UIHint(type="actions", title="Siguiente paso", options=options))

    return UIHintsOut(hints=hints)