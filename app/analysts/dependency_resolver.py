from dataclasses import dataclass, field
from typing import List

from app.analysts.legal_analyst.step_catalog import get_step_definition


@dataclass
class DependencyResolutionResult:
    is_valid: bool
    missing_dependencies: List[str] = field(default_factory=list)
    ordered_steps: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class DependencyResolver:
    def __init__(self, analyst_id: str):
        self.analyst_id = analyst_id

    def resolve(self, step_ids: List[str]) -> DependencyResolutionResult:
        """
        Valida que todos los steps tengan sus dependencias presentes
        y devuelve una secuencia ordenada sin duplicados.
        """
        if not step_ids:
            return DependencyResolutionResult(
                is_valid=False,
                missing_dependencies=[],
                ordered_steps=[],
                errors=["No se recibió ninguna secuencia de steps."],
            )

        ordered_steps: List[str] = []
        missing_dependencies: List[str] = []
        errors: List[str] = []
        visited = set()

        for step_id in step_ids:
            self._add_step_with_dependencies(
                step_id=step_id,
                ordered_steps=ordered_steps,
                missing_dependencies=missing_dependencies,
                errors=errors,
                visited=visited,
                requested_steps=set(step_ids),
            )

        is_valid = len(errors) == 0 and len(missing_dependencies) == 0

        return DependencyResolutionResult(
            is_valid=is_valid,
            missing_dependencies=missing_dependencies,
            ordered_steps=ordered_steps,
            errors=errors,
        )

    def _add_step_with_dependencies(
        self,
        step_id: str,
        ordered_steps: List[str],
        missing_dependencies: List[str],
        errors: List[str],
        visited: set,
        requested_steps: set,
    ) -> None:
        if step_id in visited:
            return

        try:
            step_definition = get_step_definition(step_id)
        except ValueError as exc:
            errors.append(str(exc))
            return

        for dependency in step_definition.depends_on:
            if dependency not in requested_steps:
                missing_dependencies.append(
                    f"El step '{step_id}' requiere la dependencia '{dependency}'."
                )
                continue

            self._add_step_with_dependencies(
                step_id=dependency,
                ordered_steps=ordered_steps,
                missing_dependencies=missing_dependencies,
                errors=errors,
                visited=visited,
                requested_steps=requested_steps,
            )

        visited.add(step_id)

        if step_id not in ordered_steps:
            ordered_steps.append(step_id)