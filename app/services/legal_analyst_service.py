from dataclasses import asdict
from typing import Any, Dict, List, Optional

from app.analysts.legal_analyst.runtime_adapter import LegalAnalystRuntimeAdapter


class LegalAnalystService:
    def __init__(self) -> None:
        self.adapter = LegalAnalystRuntimeAdapter()

    def execute_analysis(
        self,
        goal_type: str,
        inputs: Optional[Dict[str, Any]] = None,
        assigned_macro_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        result = self.adapter.execute(
            goal_type=goal_type,
            inputs=inputs or {},
            assigned_macro_steps=assigned_macro_steps or [],
        )

        serialized_result = {
            "analyst_id": result.analyst_id,
            "goal_type": result.goal_type,
            "selected_steps": result.selected_steps,
            "ordered_steps": result.ordered_steps,
            "planning_reasoning": result.planning_reasoning,
            "dependency_errors": result.dependency_errors,
            "missing_dependencies": result.missing_dependencies,
            "runtime_context": None,
            "step_ui_map": {
                "load_contract": {
                    "step_id": "load_contract",
                    "title": "Cargar contrato",
                    "chat_scope": {
                        "mode": "step_only",
                        "allowed_topics": [
                            "subida de archivo",
                            "formatos permitidos",
                            "validación del contrato",
                            "uso de este paso",
                        ],
                    },
                    "initial_messages": [
                        {
                            "id": "msg_load_contract_1",
                            "type": "assistant_text",
                            "content": "Lee tu contrato para iniciar el análisis legal.",
                            "animate": True,
                        },
                        {
                            "id": "msg_load_contract_2",
                            "type": "assistant_text",
                            "content": "Sube un archivo PDF, DOCX o TXT.",
                            "animate": True,
                        },
                    ],
                    "render_blocks": [
                        {
                            "id": "load_contract_uploader",
                            "type": "file_uploader",
                            "label": "Arrastra y suelta el archivo aquí, o súbelo desde tu equipo.",
                            "accepted_formats": ["pdf", "docx", "txt"],
                        }
                    ],
                }
            },
        }

        if result.runtime_context:
            serialized_result["runtime_context"] = {
                "analyst_id": result.runtime_context.analyst_id,
                "goal_type": result.runtime_context.goal_type,
                "inputs": result.runtime_context.inputs,
                "shared_state": result.runtime_context.shared_state,
                "step_results": [
                    asdict(step_result)
                    for step_result in result.runtime_context.step_results
                ],
            }

        return serialized_result