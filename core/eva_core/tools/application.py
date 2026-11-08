import shutil
import subprocess
import os
import time
import urllib.parse
import psutil
from typing import Dict, Any
from core.eva_core.tools.base import BaseTool
from core.eva_core.protocol import ToolResult

class ApplicationTool(BaseTool):
    name = "application_tool"
    description = "Handles safe, allowlisted application lifecycle and browser search operations."

    ALLOWLIST = {
        "chrome": ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
        "google chrome": ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
        "firefox": ("firefox", "firefox-esr"),
        "brave": ("brave-browser", "brave"),
        "brave browser": ("brave-browser", "brave"),
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "code": ("code", "code-insiders"),
        "calculator": "gnome-calculator",
        "settings": "gnome-control-center",
        "text editor": ("gnome-text-editor", "mousepad", "kate", "xed", "leafpad"),
        "gnome text editor": ("gnome-text-editor", "mousepad", "kate", "xed", "leafpad"),
        "notepad": ("gnome-text-editor", "mousepad", "kate", "xed", "leafpad"),
        "file manager": ("nautilus", "dolphin", "thunar", "pcmanfm"),
        "nautilus": ("nautilus", "dolphin", "thunar", "pcmanfm"),
    }

    BROWSER_NAMES = {"chrome", "google chrome", "firefox", "brave", "brave browser"}
    EDITOR_NAMES = {"text editor", "gnome text editor"}
    PROCESS_NAMES = {
        "google-chrome": {"google-chrome", "google-chrome-stable", "chrome", "chromium", "chromium-browser"},
        "firefox": {"firefox", "firefox-esr"},
        "brave-browser": {"brave", "brave-browser"},
        "code": {"code", "code-insiders"},
        "nautilus": {"nautilus"},
    }

    @staticmethod
    def _resolve_executable(executable: str) -> str | None:
        search_path = os.pathsep.join((os.environ.get("PATH", ""), os.defpath, "/usr/local/bin", "/usr/bin"))
        candidates = executable if isinstance(executable, (tuple, list)) else (executable,)
        for candidate in candidates:
            resolved = shutil.which(candidate, path=search_path)
            if resolved:
                return resolved
        return None

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        operation = arguments.get("operation")
        app_name = arguments.get("application")

        if not operation or not app_name:
            return ToolResult(success=False, tool_name=self.name, message="Missing operation or application name.", error="InvalidInput")

        app_name_key = app_name.lower().strip()
        if app_name_key == "notepad":
            app_name_key = "text editor"
        
        if app_name_key not in self.ALLOWLIST:
            return ToolResult(
                success=False, 
                tool_name=self.name, 
                message=f"Application '{app_name}' is not in the allowlist.", 
                error="UnauthorizedApplication"
            )

        executable = self.ALLOWLIST[app_name_key]

        try:
            if operation == "check":
                operation = "check_running"
            if operation in {"open", "focus", "check_running", "close", "minimize", "restore", "list_windows"}:
                return self._lifecycle(operation, app_name_key, executable, arguments)

            if operation == "write_text":
                return self._write_text(app_name_key, executable, arguments)

            if operation in {"search", "youtube_search"}:
                query = arguments.get("query")
                if not isinstance(query, str) or not query.strip():
                    return ToolResult(success=False, tool_name=self.name, message="Search query is required.", error="InvalidInput")
                if app_name_key not in self.BROWSER_NAMES:
                    return ToolResult(success=False, tool_name=self.name, message="Search requires an approved browser.", error="InvalidBrowser")
                resolved_executable = self._resolve_executable(executable)
                if not resolved_executable:
                    return ToolResult(success=False, tool_name=self.name, message=f"Application '{app_name}' is not installed.", error="ApplicationUnavailable")
                provider = str(arguments.get("search_provider", "youtube" if operation == "youtube_search" else "google")).lower()
                if provider not in {"google", "youtube"}:
                    return ToolResult(success=False, tool_name=self.name, message="Unsupported search provider.", error="InvalidSearchProvider")
                base_url = "https://www.youtube.com/results?search_query=" if provider == "youtube" else "https://www.google.com/search?q="
                url = base_url + urllib.parse.quote_plus(query.strip())
                command = [resolved_executable]
                if arguments.get("new_tab"):
                    command.append("--new-tab")
                command.append(url)
                subprocess.Popen(command, close_fds=True, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                message = f"Opened YouTube search for: {query.strip()}. Playback may require manual interaction." if provider == "youtube" else f"Opened search for: {query.strip()}"
                return ToolResult(success=True, tool_name=self.name, message=message, data={"application": app_name_key, "url": url, "query": query.strip(), "playback_verified": False})

            elif operation == "check":
                available = self._resolve_executable(executable) is not None
                return ToolResult(success=available, tool_name=self.name, message=f"Application {app_name} is {'available' if available else 'not installed'}.", data={"available": available})
            
            else:
                return ToolResult(success=False, tool_name=self.name, message=f"Unsupported operation: {operation}", error="UnsupportedOperation")
                
        except Exception as e:
            return ToolResult(success=False, tool_name=self.name, message="Application operation failed.", error=str(e))

    def _running_processes(self, executable):
        candidates = executable if isinstance(executable, (tuple, list)) else (executable,)
        process_names = set()
        for candidate in candidates:
            executable_name = os.path.basename(candidate).lower()
            process_names.update(self.PROCESS_NAMES.get(executable_name, {executable_name}))
        running = []
        for process in psutil.process_iter(["pid", "name", "exe"]):
            try:
                process_name = (process.info.get("name") or "").lower()
                process_exe = os.path.basename(process.info.get("exe") or "").lower()
                if process_name in process_names or process_exe in process_names:
                    running.append(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return running

    def _focus(self, process) -> bool:
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            return False
        for window_id, pid in self._windows(wmctrl):
            if pid == process.info["pid"]:
                result = subprocess.run([wmctrl, "-i", "-a", window_id], capture_output=True, text=True, timeout=3, check=False)
                return result.returncode == 0
        return False

    def _input_backend(self):
        return shutil.which("xdotool") or shutil.which("ydotool")

    def _write_text(self, app_name: str, executable, arguments: Dict[str, Any]) -> ToolResult:
        text = arguments.get("text")
        if not isinstance(text, str) or not text:
            return ToolResult(success=False, tool_name=self.name, message="Text to type is required.", error="InvalidInput")
        if app_name in self.EDITOR_NAMES:
            resolved_executable = self._resolve_executable(executable)
            if not resolved_executable:
                return ToolResult(success=False, tool_name=self.name, message="No supported text editor is installed.", error="EditorUnavailable")
        backend = self._input_backend()
        if not backend:
            return ToolResult(success=False, tool_name=self.name, message="Visible typing requires xdotool or ydotool; no compatible input backend is installed for this session.", error="InputBackendUnavailable")
        if os.path.basename(backend) == "xdotool":
            result = subprocess.run([backend, "type", "--delay", "25", text], capture_output=True, text=True, timeout=max(10, len(text) // 5), check=False)
        else:
            result = subprocess.run([backend, "type", text], capture_output=True, text=True, timeout=max(10, len(text) // 5), check=False)
        if result.returncode != 0:
            return ToolResult(success=False, tool_name=self.name, message="Visible typing failed.", error="TypingFailed")
        return ToolResult(success=True, tool_name=self.name, message="Text was typed into the active editor window.", data={"characters": len(text), "verified": False, "backend": os.path.basename(backend)})

    def _windows(self, wmctrl: str):
        result = subprocess.run([wmctrl, "-l", "-p"], capture_output=True, text=True, timeout=3, check=False)
        windows = []
        for line in result.stdout.splitlines():
            fields = line.split(None, 4)
            if len(fields) >= 3:
                try:
                    windows.append((fields[0], int(fields[2])))
                except ValueError:
                    continue
        return windows

    def _close_gracefully(self, process) -> bool:
        wmctrl = shutil.which("wmctrl")
        if wmctrl:
            windows = self._windows(wmctrl)
            matching_windows = [window_id for window_id, pid in windows if pid == process.info["pid"]]
            for window_id in matching_windows:
                subprocess.run([wmctrl, "-i", "-c", window_id], capture_output=True, text=True, timeout=3, check=False)
            if not matching_windows:
                process.terminate()
        else:
            process.terminate()
        try:
            process.wait(timeout=5)
        except psutil.TimeoutExpired:
            return False
        return not process.is_running()

    def _lifecycle(self, operation: str, app_name: str, executable: str, arguments: Dict[str, Any]) -> ToolResult:
        resolved_executable = self._resolve_executable(executable)
        running = self._running_processes(executable)
        if operation == "check_running":
            return ToolResult(success=True, tool_name=self.name, message=f"Application {app_name} is {'running' if running else 'not running'}.", data={"application": app_name, "running": bool(running)})
        if operation == "list_windows":
            wmctrl = shutil.which("wmctrl")
            if not wmctrl:
                return ToolResult(success=False, tool_name=self.name, message="Window listing requires wmctrl.", error="WindowControlUnavailable")
            return ToolResult(success=True, tool_name=self.name, message=f"Listed windows for {app_name}.", data={"windows": [{"window_id": window_id, "pid": pid} for window_id, pid in self._windows(wmctrl)]})
        if operation == "close":
            if not running:
                if not resolved_executable:
                    return ToolResult(success=False, tool_name=self.name, message=f"Application '{app_name}' is not installed.", error="ApplicationUnavailable")
                return ToolResult(success=True, tool_name=self.name, message=f"Application {app_name} is not running.", data={"application": app_name, "running": False, "closed": True})
            closed = self._close_gracefully(running[0])
            return ToolResult(success=closed, tool_name=self.name, message=f"Closed application: {app_name}" if closed else f"Could not close application: {app_name}", error=None if closed else "CloseTimeout", data={"application": app_name, "closed": closed})
        if not resolved_executable:
            return ToolResult(success=False, tool_name=self.name, message=f"Application '{app_name}' is not installed.", error="ApplicationUnavailable")
        if operation == "focus":
            if not running:
                return ToolResult(success=False, tool_name=self.name, message=f"Application {app_name} is not running.", error="ApplicationNotRunning")
            focused = self._focus(running[0])
            return ToolResult(success=focused, tool_name=self.name, message=f"Focused application: {app_name}" if focused else f"Could not focus application: {app_name}", error=None if focused else "FocusUnavailable", data={"application": app_name, "running": True, "focused": focused})
        if operation in {"minimize", "restore"}:
            wmctrl = shutil.which("wmctrl")
            if not wmctrl:
                return ToolResult(success=False, tool_name=self.name, message="Window minimize/restore requires wmctrl.", error="WindowControlUnavailable")
            windows = [window_id for window_id, pid in self._windows(wmctrl) if any(process.info["pid"] == pid for process in running)]
            if not windows:
                return ToolResult(success=False, tool_name=self.name, message=f"No visible window found for {app_name}.", error="WindowNotFound")
            command = [wmctrl, "-i", "-r", windows[0], "-b", "add,hidden" if operation == "minimize" else "remove,hidden"]
            result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
            return ToolResult(success=result.returncode == 0, tool_name=self.name, message=f"{operation.title()}d {app_name}." if result.returncode == 0 else f"Could not {operation} {app_name}.", error=None if result.returncode == 0 else "WindowControlFailed")
        if running and not arguments.get("new_window"):
            focused = self._focus(running[0])
            if focused:
                return ToolResult(success=True, tool_name=self.name, message=f"Focused existing application: {app_name}", data={"application": app_name, "focused": True, "launched": False})
            return ToolResult(success=True, tool_name=self.name, message=f"Application {app_name} is already running. Window focus could not be verified in this desktop session.", data={"application": app_name, "focused": False, "focus_verified": False, "already_running": True, "launched": False})
        command = [resolved_executable]
        if arguments.get("new_window"):
            command.append("--new-window")
        subprocess.Popen(command, close_fds=True, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if self._running_processes(executable):
                return ToolResult(success=True, tool_name=self.name, message=f"Launched application: {app_name}", data={"application": app_name, "focused": False, "launched": True, "verified_running": True})
            time.sleep(0.1)
        return ToolResult(success=False, tool_name=self.name, message=f"Launch requested but application {app_name} was not verified as running.", error="LaunchUnverified", data={"application": app_name, "launched": True, "verified_running": False})
