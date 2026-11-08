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
        if not isinstance(relative_path, str) or os.path.isabs(relative_path):
            raise ValueError("Absolute paths are not allowed.")

        workspace_root = os.path.realpath(WORKSPACE_ROOT)
        absolute_path = os.path.realpath(os.path.join(workspace_root, relative_path))
        try:
            within_workspace = os.path.commonpath((workspace_root, absolute_path)) == workspace_root
        except ValueError:
            within_workspace = False
        if not within_workspace:
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
                parent_path = os.path.realpath(os.path.dirname(target_path))
                if os.path.commonpath((os.path.realpath(WORKSPACE_ROOT), parent_path)) != os.path.realpath(WORKSPACE_ROOT):
                    raise ValueError("File parent is outside the workspace.")
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return ToolResult(success=True, tool_name=self.name, message=f"Created file: {path}")

            elif operation == "read_file":
                if not os.path.exists(target_path):
                    return ToolResult(success=False, tool_name=self.name, message="File not found.", error="FileNotFound")
                with open(target_path, "r", encoding="utf-8") as f:
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
