from typing import Dict, Any
from core.eva_core.tools.base import BaseTool
from core.eva_core.protocol import ToolResult

class EchoTool(BaseTool):
    name = "echo"
    description = "Echoes the provided input text back as output."

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        text = arguments.get("text", "")
        return ToolResult(
            success=True,
            tool_name=self.name,
            message="Echo successful.",
            data={"echo_output": text}
        )
