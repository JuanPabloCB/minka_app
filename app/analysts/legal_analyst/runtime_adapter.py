from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.analysts.dependency_resolver import DependencyResolver
from app.analysts.planner import AnalystPlanner, PlannerDecision
from app.analysts.runtime import AnalystRuntime, AnalystRuntimeContext
from app.analysts.legal_analyst.definition import LEGAL_ANALYST_DEFINITION


@dataclass
class LegalAnalystExecutionResult:
    analyst_id: str
    goal_type: str
    selected_steps: List[str] = field(default_factory=list)
    ordered_steps: List[str] = field(default_factory=list)
    planning_reasoning: List[str] = field(default_factory=list)
    dependency_errors: List[str] = field(default_factory=list)
    missing_dependencies: List[str] = field(default_factory=list)
    runtime_context: Optional[AnalystRuntimeContext] = None


class LegalAnalystRuntimeAdapter:
    def __init__(self) -> None:
        self.analyst_id = LEGAL_ANALYST_DEFINITION.analyst_id
        self.planner = AnalystPlanner(analyst_id=self.analyst_id)
        self.dependency_resolver = DependencyResolver(analyst_id=self.analyst_id)
        self.runtime = AnalystRuntime(analyst_id=self.analyst_id)

    def execute(
        self,
        goal_type: str,
        inputs: Optional[Dict[str, Any]] = None,
        assigned_macro_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> LegalAnalystExecutionResult:
        """
        Orquesta la ejecución completa del Analista Legal:
        1. Planea los steps
        2. Resuelve dependencias
        3. Ejecuta la secuencia válida
        """
        inputs = inputs or {}
        assigned_macro_steps = assigned_macro_steps or []

        planning_decision: PlannerDecision = self.planner.build_plan(
            goal_type=goal_type,
            inputs=inputs,
            assigned_macro_steps=assigned_macro_steps,
        )

        dependency_result = self.dependency_resolver.resolve(
            planning_decision.selected_steps
        )

        if not dependency_result.is_valid:
            return LegalAnalystExecutionResult(
                analyst_id=self.analyst_id,
                goal_type=goal_type,
                selected_steps=planning_decision.selected_steps,
                ordered_steps=dependency_result.ordered_steps,
                planning_reasoning=planning_decision.reasoning,
                dependency_errors=dependency_result.errors,
                missing_dependencies=dependency_result.missing_dependencies,
                runtime_context=None,
            )

        runtime_context = self.runtime.run(
            goal_type=goal_type,
            step_ids=dependency_result.ordered_steps,
            inputs=inputs,
        )

        return LegalAnalystExecutionResult(
            analyst_id=self.analyst_id,
            goal_type=goal_type,
            selected_steps=planning_decision.selected_steps,
            ordered_steps=dependency_result.ordered_steps,
            planning_reasoning=planning_decision.reasoning,
            dependency_errors=[],
            missing_dependencies=[],
            runtime_context=runtime_context,
        )