from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMProvider(ABC):
    @abstractmethod
    async def generate_json(self, prompt: str, system: str = "") -> Dict[str, Any]:
        """Generate a JSON response from the LLM provider."""
        pass

class PlanningProvider(ABC):
    @abstractmethod
    async def generate_plan(self, prompt: str, system: str = "") -> Dict[str, Any]:
        """Generate a JSON task plan from the planning provider."""
        pass
