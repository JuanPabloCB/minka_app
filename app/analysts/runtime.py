from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from app.analysts.base_step import BaseStep, BaseStepResult
from app.analysts.legal_analyst.step_catalog import get_step_definition
from app.analysts.legal_analyst.steps.detect_findings_step import DetectFindingsStep
from app.analysts.legal_analyst.steps.generate_marked_contract_step import GenerateMarkedContractStep
from app.analysts.legal_analyst.steps.load_contract_step import LoadContractStep
from app.analysts.legal_analyst.steps.practical_interpretation_step import PracticalInterpretationStep
from app.analysts.legal_analyst.steps.proritize_risks_step import PrioritizeRisksStep


@dataclass
class StepExecutionResult:
    step_id: str
    status: str
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class AnalystRuntimeContext:
    analyst_id: str
    goal_type: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    step_results: List[StepExecutionResult] = field(default_factory=list)


class AnalystRuntime:
    def __init__(self, analyst_id: str):
        self.analyst_id = analyst_id
        self.step_registry: Dict[str, Type[BaseStep]] = {
            "load_contract": LoadContractStep,
            "detect_findings": DetectFindingsStep,
            "prioritize_risks": PrioritizeRisksStep,
            "practical_interpretation": PracticalInterpretationStep,
            "generate_marked_contract": GenerateMarkedContractStep,
        }

    def validate_step_sequence(self, step_ids: List[str]) -> None:
        """
        Valida que todos los steps existan y que sus dependencias
        aparezcan antes dentro de la secuencia enviada.
        """
        executed_so_far = set()

        for step_id in step_ids:
            step_definition = get_step_definition(step_id)

            if step_id not in self.step_registry:
                raise ValueError(
                    f"El step '{step_id}' no tiene implementación registrada en runtime."
                )

            for dependency in step_definition.depends_on:
                if dependency not in executed_so_far:
                    raise ValueError(
                        f"El step '{step_id}' requiere que '{dependency}' "
                        f"se ejecute antes en la secuencia."
                    )

            executed_so_far.add(step_id)

    def run(
        self,
        goal_type: str,
        step_ids: List[str],
        inputs: Optional[Dict[str, Any]] = None,
    ) -> AnalystRuntimeContext:
        """
        Ejecuta la secuencia de steps en orden usando las implementaciones reales
        registradas en step_registry.
        """
        if not step_ids:
            raise ValueError("La ejecución requiere al menos un step.")

        self.validate_step_sequence(step_ids)

        context = AnalystRuntimeContext(
            analyst_id=self.analyst_id,
            goal_type=goal_type,
            inputs=inputs or {},
            shared_state={},
            step_results=[],
        )

        for step_id in step_ids:
            result = self.execute_step(step_id, context)
            context.step_results.append(result)

            if result.status != "completed":
                break

            context.shared_state[step_id] = result.output

        return context

    def execute_step(
        self,
        step_id: str,
        context: AnalystRuntimeContext,
    ) -> StepExecutionResult:
        """
        Ejecuta un step individual usando su clase real.
        """
        get_step_definition(step_id)

        step_class = self.step_registry.get(step_id)
        if not step_class:
            return StepExecutionResult(
                step_id=step_id,
                status="failed",
                output={},
                error=f"No existe una clase registrada para el step '{step_id}'.",
            )

        try:
            step_instance = step_class()

            step_context = {
                "analyst_id": context.analyst_id,
                "goal_type": context.goal_type,
                "inputs": context.inputs,
                "shared_state": context.shared_state,
                "step_results": context.step_results,
            }

            step_result: BaseStepResult = step_instance.execute(step_context)

            return StepExecutionResult(
                step_id=step_result.step_id,
                status=step_result.status,
                output=step_result.output,
                error=step_result.error,
            )

        except Exception as exc:
            return StepExecutionResult(
                step_id=step_id,
                status="failed",
                output={},
                error=str(exc),
            )