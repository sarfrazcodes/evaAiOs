import logging
from typing import Dict, Optional
from core.eva_core.tools.base import BaseTool

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} is already registered.")
        self._tools[tool.name] = tool
        logging.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> Dict[str, str]:
        return {name: tool.description for name, tool in self._tools.items()}
