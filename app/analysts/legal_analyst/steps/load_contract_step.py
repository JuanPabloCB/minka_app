from typing import Any, Dict

from app.analysts.base_step import BaseStep, BaseStepResult


class LoadContractStep(BaseStep):
    step_id = "load_contract"
    name = "Cargar contrato"
    description = (
        "Recibe el contrato desde el orquestador o desde carga directa del usuario, "
        "y prepara el contexto documental para el análisis legal."
    )

    def execute(self, context: Dict[str, Any]) -> BaseStepResult:
        self.validate()

        inputs = context.get("inputs", {}) or {}

        document_id = inputs.get("document_id")
        uploaded_file = inputs.get("uploaded_file")
        filename = inputs.get("filename")
        source = inputs.get("source", "direct")

        if document_id:
            return BaseStepResult(
                step_id=self.step_id,
                status="completed",
                output={
                    "document_source": "orchestrator_or_existing_context",
                    "document_id": document_id,
                    "filename": filename,
                    "source": source,
                    "message": (
                        "Se reutilizó un documento ya disponible en el contexto "
                        "sin necesidad de volver a subirlo."
                    ),
                    "document_ready": True,
                },
                error=None,
            )

        if uploaded_file:
            inferred_filename = filename or getattr(uploaded_file, "filename", None)

            return BaseStepResult(
                step_id=self.step_id,
                status="completed",
                output={
                    "document_source": "direct_upload",
                    "document_id": None,
                    "filename": inferred_filename,
                    "source": source,
                    "message": (
                        "Se recibió un archivo cargado directamente y quedó listo "
                        "para el análisis legal."
                    ),
                    "document_ready": True,
                },
                error=None,
            )

        return BaseStepResult(
            step_id=self.step_id,
            status="failed",
            output={
                "document_ready": False,
            },
            error=(
                "No se encontró ningún contrato disponible. "
                "Se requiere 'document_id' o 'uploaded_file'."
            ),
        )