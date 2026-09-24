import os
from typing import Dict, Any
from core.eva_core.tools.base import BaseTool
from core.eva_core.protocol import ToolResult

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../workspace'))

class FileTool(BaseTool):
    name = "file_tool"
    description = "Handles minimal safe file operations within the designated workspace."

    def __init__(self):
        if not os.path.exists(WORKSPACE_ROOT):
            os.makedirs(WORKSPACE_ROOT, exist_ok=True)

    def _resolve_path(self, relative_path: str) -> str:
        """Resolves and validates a path against the WORKSPACE_ROOT to prevent traversal."""
        # Ensure path doesn't start with a slash which makes join ignore WORKSPACE_ROOT
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]
            
        absolute_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, relative_path))
        if not absolute_path.startswith(WORKSPACE_ROOT):
            raise ValueError(f"Path traversal detected: {relative_path} is outside the workspace.")
        return absolute_path

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        operation = arguments.get("operation")
        path = arguments.get("path")
        content = arguments.get("content", "")

        if not operation or not path:
            return ToolResult(success=False, tool_name=self.name, message="Missing operation or path.", error="InvalidInput")

        try:
            target_path = self._resolve_path(path)

            if operation == "create_file":
                with open(target_path, "w") as f:
                    f.write(content)
                return ToolResult(success=True, tool_name=self.name, message=f"Created file: {path}")

            elif operation == "read_file":
                if not os.path.exists(target_path):
                    return ToolResult(success=False, tool_name=self.name, message="File not found.", error="FileNotFound")
                with open(target_path, "r") as f:
                    file_content = f.read()
                return ToolResult(success=True, tool_name=self.name, message=f"Read file: {path}", data={"content": file_content})

            elif operation == "list_directory":
                if not os.path.exists(target_path) or not os.path.isdir(target_path):
                    return ToolResult(success=False, tool_name=self.name, message="Directory not found.", error="DirectoryNotFound")
                items = os.listdir(target_path)
                return ToolResult(success=True, tool_name=self.name, message=f"Listed directory: {path}", data={"items": items})

            elif operation == "create_directory":
                os.makedirs(target_path, exist_ok=True)
                return ToolResult(success=True, tool_name=self.name, message=f"Created directory: {path}")

            else:
                return ToolResult(success=False, tool_name=self.name, message=f"Unsupported operation: {operation}", error="UnsupportedOperation")

        except ValueError as ve:
            return ToolResult(success=False, tool_name=self.name, message="Security violation.", error=str(ve))
        except Exception as e:
            return ToolResult(success=False, tool_name=self.name, message="File operation failed.", error=str(e))
