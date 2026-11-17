import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List
from core.eva_core.tools.base import BaseTool
from core.eva_core.protocol import ToolResult

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../workspace'))

class FileTool(BaseTool):
    name = "file_tool"
    description = "Handles safe workspace file operations: create, read, edit, append, search, code generation, and inspection."

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
        path = arguments.get("path", "")
        content = arguments.get("content", "")

        if not operation:
            return ToolResult(success=False, tool_name=self.name, message="Missing operation.", error="InvalidInput")

        # Allow search_files without explicit path (defaults to root)
        if operation == "search_files" and not path:
            path = "."

        if not path and operation != "search_files":
            return ToolResult(success=False, tool_name=self.name, message="Missing path.", error="InvalidInput")

        try:
            target_path = self._resolve_path(path)

            if operation == "create_file":
                parent_path = os.path.realpath(os.path.dirname(target_path))
                if os.path.commonpath((os.path.realpath(WORKSPACE_ROOT), parent_path)) != os.path.realpath(WORKSPACE_ROOT):
                    raise ValueError("File parent is outside the workspace.")
                os.makedirs(parent_path, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)
                line_count = len(content.splitlines())
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    message=f"Created file: {path}",
                    data={"path": path, "lines": line_count, "bytes": len(content.encode("utf-8"))}
                )

            elif operation == "read_file":
                if not os.path.exists(target_path):
                    return ToolResult(success=False, tool_name=self.name, message="File not found.", error="FileNotFound")
                with open(target_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                return ToolResult(success=True, tool_name=self.name, message=f"Read file: {path}", data={"content": file_content})

            elif operation == "edit_file":
                if not os.path.exists(target_path):
                    return ToolResult(success=False, tool_name=self.name, message="File not found.", error="FileNotFound")
                target = arguments.get("target")
                replacement = arguments.get("replacement", arguments.get("content", ""))
                with open(target_path, "r", encoding="utf-8") as f:
                    existing = f.read()

                if target is not None:
                    if target not in existing:
                        return ToolResult(success=False, tool_name=self.name, message=f"Target text not found in {path}", error="TargetNotFound")
                    new_content = existing.replace(target, replacement, 1 if arguments.get("single_match", True) else -1)
                else:
                    new_content = replacement

                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                lines = len(new_content.splitlines())
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    message=f"Successfully edited file: {path}",
                    data={"path": path, "lines": lines, "bytes": len(new_content.encode("utf-8"))}
                )

            elif operation == "append_file":
                parent_path = os.path.realpath(os.path.dirname(target_path))
                os.makedirs(parent_path, exist_ok=True)
                with open(target_path, "a", encoding="utf-8") as f:
                    f.write(content)
                with open(target_path, "r", encoding="utf-8") as f:
                    total_lines = len(f.readlines())
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    message=f"Appended to file: {path}",
                    data={"path": path, "lines": total_lines, "bytes_appended": len(content.encode("utf-8"))}
                )

            elif operation == "generate_code":
                code = arguments.get("code", arguments.get("content", ""))
                language = arguments.get("language", "text")
                parent_path = os.path.realpath(os.path.dirname(target_path))
                os.makedirs(parent_path, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(code)
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    message=f"Generated {language} code at: {path}",
                    data={"path": path, "language": language, "lines": len(code.splitlines())}
                )

            elif operation == "search_files":
                query = arguments.get("query", arguments.get("pattern", "")).lower()
                results: List[Dict[str, Any]] = []
                base_dir = target_path if os.path.isdir(target_path) else os.path.realpath(WORKSPACE_ROOT)
                for root, _, files in os.walk(base_dir):
                    for file in files:
                        full = os.path.join(root, file)
                        rel = os.path.relpath(full, os.path.realpath(WORKSPACE_ROOT))
                        matched = False
                        match_snippet = ""
                        if not query or query in file.lower():
                            matched = True
                        else:
                            try:
                                with open(full, "r", encoding="utf-8", errors="ignore") as f:
                                    for line_no, line in enumerate(f, 1):
                                        if query in line.lower():
                                            matched = True
                                            match_snippet = line.strip()[:100]
                                            break
                            except Exception:
                                pass
                        if matched:
                            results.append({"path": rel, "name": file, "snippet": match_snippet})
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    message=f"Found {len(results)} matches in workspace",
                    data={"matches": results, "count": len(results)}
                )

            elif operation == "file_info":
                if not os.path.exists(target_path):
                    return ToolResult(success=False, tool_name=self.name, message="File not found.", error="FileNotFound")
                stat = os.stat(target_path)
                is_dir = os.path.isdir(target_path)
                line_count = 0
                if not is_dir:
                    try:
                        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                            line_count = sum(1 for _ in f)
                    except Exception:
                        pass
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    message=f"File info for: {path}",
                    data={
                        "path": path,
                        "is_dir": is_dir,
                        "is_file": not is_dir,
                        "size_bytes": stat.st_size,
                        "line_count": line_count,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    }
                )

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
