#traductor de plan_steps a analyst_actions
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.db.models.plan_step import PlanStep


@dataclass(frozen=True)
class AnalystActionStep:
    key: str
    label: str
    status: str
    estimated_minutes: int


LEGAL_ACTION_CATALOG: dict[str, dict[str, str | int]] = {
    "parse": {
        "label": "Leer contrato",
        "estimated_minutes": 8,
    },
    "classify": {
        "label": "Detectar estructura",
        "estimated_minutes": 10,
    },
    "segment": {
        "label": "Segmentar cláusulas",
        "estimated_minutes": 16,
    },
    "detect_risk": {
        "label": "Detectar riesgos",
        "estimated_minutes": 18,
    },
    "detect_missing": {
        "label": "Detectar cláusulas faltantes",
        "estimated_minutes": 16,
    },
    "explain": {
        "label": "Explicar cláusulas",
        "estimated_minutes": 12,
    },
    "highlight": {
        "label": "Resaltar cláusulas",
        "estimated_minutes": 10,
    },
    "report": {
        "label": "Generar informe final",
        "estimated_minutes": 12,
    },
}


LEGAL_ACTION_ORDER = [
    "parse",
    "classify",
    "segment",
    "detect_risk",
    "detect_missing",
    "explain",
    "highlight",
    "report",
]


def build_analyst_actions_for_steps(
    *,
    analyst_key: str,
    plan_steps: Iterable[PlanStep],
) -> list[AnalystActionStep]:
    """
    Traduce plan_steps de alto nivel a acciones canónicas del analista.

    V1:
    - solo soporta legal_analyst
    - usa heurística determinística basada en títulos
    - deduplica acciones y respeta orden canónico
    """
    plan_steps = list(plan_steps)

    if not plan_steps:
        return []

    if analyst_key == "legal_analyst":
        action_keys = _map_plan_steps_to_legal_actions(plan_steps)
        return [_build_legal_action_step(key) for key in action_keys]

    return []


def _map_plan_steps_to_legal_actions(plan_steps: list[PlanStep]) -> list[str]:
    requested: set[str] = set()

    for step in plan_steps:
        title = (step.title or "").strip().lower()
        if not title:
            continue

        # Recepción / lectura / entrada del documento
        if _contains_any(
            title,
            {
                "recibir",
                "archivo",
                "documento",
                "contrato",
                "cargar",
                "adjuntar",
                "input",
            },
        ):
            requested.add("parse")

        # Análisis general / estructura / clasificación
        if _contains_any(
            title,
            {
                "analizar",
                "análisis",
                "analisis",
                "contenido",
                "estructura",
                "clasificar",
                "clasificación",
                "clasificacion",
                "tipo",
                "categorizar",
            },
        ):
            requested.add("classify")

        # Segmentación / detección de cláusulas
        if _contains_any(
            title,
            {
                "segmentar",
                "segmentación",
                "segmentacion",
                "cláusula",
                "clausula",
                "cláusulas",
                "clausulas",
                "listar cláusulas",
                "listar clausulas",
                "detectar cláusulas",
                "detectar clausulas",
            },
        ):
            requested.add("segment")

        # Riesgos / criticidad
        if _contains_any(
            title,
            {
                "riesgo",
                "riesgos",
                "crítica",
                "critica",
                "críticas",
                "criticas",
                "red flag",
                "red flags",
            },
        ):
            requested.add("detect_risk")

        # Cláusulas faltantes / vacíos / omisiones
        if _contains_any(
            title,
            {
                "faltante",
                "faltantes",
                "missing",
                "omisión",
                "omision",
                "vacío",
                "vacio",
                "vacíos",
                "vacios",
            },
        ):
            requested.add("detect_missing")

        # Explicación / desglose / revisión interpretativa
        if _contains_any(
            title,
            {
                "explicar",
                "explicación",
                "explicacion",
                "detallado",
                "detalle",
                "revisar informe",
                "interpretar",
                "explicar cláusulas",
                "explicar clausulas",
            },
        ):
            requested.add("explain")

        # Marcado / resaltar
        if _contains_any(
            title,
            {
                "resaltar",
                "subrayar",
                "marcar",
                "highlight",
            },
        ):
            requested.add("highlight")

        # Informe / reporte / salida final
        if _contains_any(
            title,
            {
                "informe",
                "reporte",
                "report",
                "pdf",
                "word",
                "entregar",
                "generar output",
                "salida",
                "entregable",
                "formato pdf",
                "formato word",
            },
        ):
            requested.add("report")

    # Reglas mínimas de dependencia / sentido común
    if "segment" in requested:
        requested.add("parse")

    if "classify" in requested:
        requested.add("parse")

    if "detect_risk" in requested:
        requested.add("parse")
        requested.add("classify")
        requested.add("segment")

    if "detect_missing" in requested:
        requested.add("parse")
        requested.add("classify")
        requested.add("segment")

    if "explain" in requested:
        requested.add("parse")
        requested.add("classify")
        requested.add("segment")

    if "highlight" in requested:
        requested.add("parse")
        requested.add("classify")
        requested.add("segment")

    if "report" in requested:
        requested.add("parse")

    return [key for key in LEGAL_ACTION_ORDER if key in requested]


def _build_legal_action_step(action_key: str) -> AnalystActionStep:
    cfg = LEGAL_ACTION_CATALOG.get(action_key)
    if not cfg:
        raise ValueError(f"Unsupported legal analyst action: {action_key}")

    return AnalystActionStep(
        key=action_key,
        label=str(cfg["label"]),
        status="pending",
        estimated_minutes=int(cfg["estimated_minutes"]),
    )


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)