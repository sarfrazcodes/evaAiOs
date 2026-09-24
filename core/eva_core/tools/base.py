from abc import ABC, abstractmethod
from typing import Dict, Any
from core.eva_core.protocol import ToolResult

class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Executes the tool with the given arguments and returns a structured ToolResult."""
        pass
