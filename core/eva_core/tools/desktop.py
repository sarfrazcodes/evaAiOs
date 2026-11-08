import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from core.eva_core.protocol import ToolResult
from core.eva_core.tools.base import BaseTool


class DesktopTool(BaseTool):
    name = "desktop_tool"
    description = "Performs narrowly scoped approved directory and audio controls."

    def __init__(self) -> None:
        home = Path.home().resolve()
        self.approved_roots = tuple(path for path in (home, home / "Downloads", Path.cwd().resolve()) if path.exists())

    def _approved_directory(self, requested_path: str) -> Path:
        candidate = Path(requested_path).expanduser().resolve()
        if not candidate.is_dir():
            raise ValueError("Directory not found.")
        if not any(candidate == root or root in candidate.parents for root in self.approved_roots):
            raise PermissionError("Directory is outside approved locations.")
        return candidate

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        operation = arguments.get("operation")
        if operation in {"read_volume", "set_volume", "mute", "unmute"}:
            return self._execute_audio(operation, arguments)

        requested_path = arguments.get("path")
        if operation != "open_directory" or not isinstance(requested_path, str) or not requested_path.strip():
            return ToolResult(success=False, tool_name=self.name, message="Only open_directory with a path is supported.", error="InvalidInput")
        try:
            directory = self._approved_directory(requested_path)
            opener = shutil.which("xdg-open", path=os.pathsep.join((os.environ.get("PATH", ""), os.defpath, "/usr/local/bin", "/usr/bin")))
            if not opener:
                return ToolResult(success=False, tool_name=self.name, message="The desktop opener is not installed.", error="UtilityUnavailable")
            subprocess.Popen([opener, str(directory)], close_fds=True, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(success=True, tool_name=self.name, message=f"Opened directory: {directory}", data={"path": str(directory)})
        except PermissionError as exc:
            return ToolResult(success=False, tool_name=self.name, message="Directory is not approved.", error=str(exc))
        except ValueError as exc:
            return ToolResult(success=False, tool_name=self.name, message=str(exc), error="DirectoryNotFound")
        except FileNotFoundError:
            return ToolResult(success=False, tool_name=self.name, message="The desktop opener is not installed.", error="UtilityUnavailable")
        except OSError as exc:
            return ToolResult(success=False, tool_name=self.name, message="Could not open directory.", error=str(exc))

    def _wpctl(self) -> str | None:
        return shutil.which(
            "wpctl",
            path=os.pathsep.join((os.environ.get("PATH", ""), os.defpath, "/usr/local/bin", "/usr/bin")),
        )

    def _execute_audio(self, operation: str, arguments: Dict[str, Any]) -> ToolResult:
        executable = self._wpctl()
        if not executable:
            return ToolResult(success=False, tool_name=self.name, message="Audio control utility is not installed.", error="UtilityUnavailable")

        if operation == "set_volume":
            value = arguments.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
                return ToolResult(success=False, tool_name=self.name, message="Volume must be a number from 0 to 100.", error="InvalidVolume")
            command = [executable, "set-volume", "@DEFAULT_AUDIO_SINK@", f"{value / 100:.2f}"]
        elif operation == "read_volume":
            command = [executable, "get-volume", "@DEFAULT_AUDIO_SINK@"]
        elif operation == "mute":
            command = [executable, "set-mute", "@DEFAULT_AUDIO_SINK@", "1"]
        else:
            command = [executable, "set-mute", "@DEFAULT_AUDIO_SINK@", "0"]

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, tool_name=self.name, message="Audio control timed out.", error="ToolTimeout")
        except OSError as exc:
            return ToolResult(success=False, tool_name=self.name, message="Audio control failed.", error=str(exc))

        if result.returncode != 0:
            return ToolResult(success=False, tool_name=self.name, message="Audio control failed.", error=result.stderr.strip() or "AudioControlError")

        if operation == "read_volume":
            match = re.search(r"Volume:\s*([0-9.]+)", result.stdout)
            if not match:
                return ToolResult(success=False, tool_name=self.name, message="Could not read the current volume.", error="InvalidAudioState")
            value = round(float(match.group(1)) * 100, 1)
            return ToolResult(success=True, tool_name=self.name, message=f"Volume is {value:g} percent.", data={"volume": value})

        message = {
            "set_volume": f"Set volume to {arguments['value']:g} percent.",
            "mute": "Muted audio.",
            "unmute": "Unmuted audio.",
        }[operation]
        return ToolResult(success=True, tool_name=self.name, message=message, data={"operation": operation})