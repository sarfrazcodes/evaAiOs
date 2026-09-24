from typing import Dict, Any
from core.eva_core.tools.base import BaseTool
from core.eva_core.protocol import ToolResult

class ApplicationTool(BaseTool):
    name = "application_tool"
    description = "Handles opening safe, approved applications."

    ALLOWLIST = {
        "terminal": "gnome-terminal",
        "chrome": "google-chrome",
        "firefox": "firefox",
        "notepad": "gedit"
    }

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        operation = arguments.get("operation")
        app_name = arguments.get("application")

        if not operation or not app_name:
            return ToolResult(success=False, tool_name=self.name, message="Missing operation or application name.", error="InvalidInput")

        app_name_key = app_name.lower().strip()
        
        if app_name_key not in self.ALLOWLIST:
            return ToolResult(
                success=False, 
                tool_name=self.name, 
                message=f"Application '{app_name}' is not in the allowlist.", 
                error="UnauthorizedApplication"
            )

        executable = self.ALLOWLIST[app_name_key]

        try:
            if operation == "open":
                # In Phase 2D, we just return a mock success for deterministic testing without weakening security
                return ToolResult(success=True, tool_name=self.name, message=f"Mock launched application: {app_name}")

            elif operation == "check":
                return ToolResult(success=True, tool_name=self.name, message=f"Application {app_name} is available.", data={"available": True})
            
            else:
                return ToolResult(success=False, tool_name=self.name, message=f"Unsupported operation: {operation}", error="UnsupportedOperation")
                
        except Exception as e:
            return ToolResult(success=False, tool_name=self.name, message="Application operation failed.", error=str(e))
