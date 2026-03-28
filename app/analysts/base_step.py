from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class BaseStepResult:
    step_id: str
    status: str
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BaseStep(ABC):
    step_id: str = ""
    name: str = ""
    description: str = ""

    def validate(self) -> None:
        """
        Validación mínima común para cualquier step.
        """
        if not self.step_id:
            raise ValueError("Todo step debe definir 'step_id'.")
        if not self.name:
            raise ValueError(f"El step '{self.step_id}' debe definir 'name'.")
        if not self.description:
            raise ValueError(f"El step '{self.step_id}' debe definir 'description'.")

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> BaseStepResult:
        """
        Método principal que cada step debe implementar.
        """
        raise NotImplementedError("Cada step debe implementar el método execute().")