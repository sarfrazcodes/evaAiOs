import os
import pytest
from core.eva_core.tools.echo import EchoTool
from core.eva_core.tools.calculator import CalculatorTool
from core.eva_core.tools.file import FileTool, WORKSPACE_ROOT
from core.eva_core.tools.application import ApplicationTool
from core.eva_core.tools.desktop import DesktopTool

def test_echo_tool():
    tool = EchoTool()
    res = tool.execute({"text": "hello"})
    assert res.success
    assert res.data["echo_output"] == "hello"

def test_calculator_tool():
    tool = CalculatorTool()
    res = tool.execute({"operation": "add", "a": 5, "b": 3})
    assert res.success
    assert res.data["result"] == 8
    
    res_div = tool.execute({"operation": "divide", "a": 10, "b": 0})
    assert not res_div.success
    assert res_div.error == "MathError"

def test_file_tool_traversal():
    tool = FileTool()
    res = tool.execute({"operation": "read_file", "path": "../../../etc/passwd"})
    assert not res.success
    assert "Security violation" in res.message

def test_file_tool_rejects_absolute_and_symlink_escape(tmp_path):
    tool = FileTool()
    absolute = tool.execute({"operation": "read_file", "path": "/etc/passwd"})
    assert not absolute.success

    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = os.path.join(WORKSPACE_ROOT, "outside-link.txt")
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are unavailable on this filesystem")
    try:
        escaped = tool.execute({"operation": "read_file", "path": "outside-link.txt"})
        assert not escaped.success
        assert "Path traversal detected" in escaped.error
    finally:
        os.unlink(link)

def test_file_tool_success():
    tool = FileTool()
    test_file = "test_write.txt"
    res = tool.execute({"operation": "create_file", "path": test_file, "content": "data"})
    assert res.success
    
    res_read = tool.execute({"operation": "read_file", "path": test_file})
    assert res_read.success
    assert res_read.data["content"] == "data"
    
    try:
        os.remove(os.path.join(WORKSPACE_ROOT, test_file))
    except FileNotFoundError:
        pass

def test_application_tool(monkeypatch):
    tool = ApplicationTool()
    monkeypatch.setattr("core.eva_core.tools.application.shutil.which", lambda name, path=None: "/usr/bin/google-chrome" if name == "google-chrome" else None)
    launched = []
    process = type("Process", (), {"info": {"pid": 1, "name": "google-chrome", "exe": "/usr/bin/google-chrome"}})()
    running = []
    monkeypatch.setattr(tool, "_running_processes", lambda executable: running)
    def fake_popen(args, **kwargs):
        launched.append(args)
        running.append(process)
    monkeypatch.setattr("core.eva_core.tools.application.subprocess.Popen", fake_popen)
    res = tool.execute({"operation": "open", "application": "chrome"})
    assert res.success
    assert launched == [["/usr/bin/google-chrome"]]
    
    res_fail = tool.execute({"operation": "open", "application": "malware"})
    assert not res_fail.success
    assert res_fail.error == "UnauthorizedApplication"

def test_application_tool_rejects_unavailable_app(monkeypatch):
    monkeypatch.setattr("core.eva_core.tools.application.shutil.which", lambda _, path=None: None)
    res = ApplicationTool().execute({"operation": "open", "application": "chrome"})
    assert not res.success
    assert res.error == "ApplicationUnavailable"

def test_application_tool_supports_installed_desktop_alias(monkeypatch):
    tool = ApplicationTool()
    launched = []
    running = []
    monkeypatch.setattr("core.eva_core.tools.application.shutil.which", lambda name, path=None: "/usr/bin/gnome-control-center" if name == "gnome-control-center" else None)
    monkeypatch.setattr(tool, "_running_processes", lambda executable: running)
    monkeypatch.setattr("core.eva_core.tools.application.subprocess.Popen", lambda args, **kwargs: launched.append(args) or running.append(type("Process", (), {"info": {"pid": 2, "name": "gnome-control-center", "exe": "/usr/bin/gnome-control-center"}})()))

    result = tool.execute({"operation": "open", "application": "settings"})

    assert result.success
    assert launched == [["/usr/bin/gnome-control-center"]]

def test_application_tool_focuses_running_app(monkeypatch):
    tool = ApplicationTool()
    process = type("Process", (), {"info": {"pid": 42, "name": "google-chrome", "exe": "/usr/bin/google-chrome"}})()
    monkeypatch.setattr(tool, "_running_processes", lambda executable: [process])
    monkeypatch.setattr("core.eva_core.tools.application.shutil.which", lambda name, path=None: "/usr/bin/wmctrl" if name == "wmctrl" else "/usr/bin/google-chrome")
    commands = []
    monkeypatch.setattr("core.eva_core.tools.application.subprocess.run", lambda command, **kwargs: commands.append(command) or type("Result", (), {"returncode": 0, "stdout": "00000001  0 42 host window\n"})())
    monkeypatch.setattr("core.eva_core.tools.application.subprocess.Popen", lambda *args, **kwargs: pytest.fail("must not launch a second instance"))
    result = tool.execute({"operation": "open", "application": "chrome"})
    assert result.success
    assert commands == [["/usr/bin/wmctrl", "-l", "-p"], ["/usr/bin/wmctrl", "-i", "-a", "00000001"]]

def test_application_tool_does_not_duplicate_when_focus_unavailable(monkeypatch):
    tool = ApplicationTool()
    process = type("Process", (), {"info": {"pid": 42, "name": "google-chrome", "exe": "/usr/bin/google-chrome"}})()
    monkeypatch.setattr(tool, "_running_processes", lambda executable: [process])
    monkeypatch.setattr(tool, "_focus", lambda process: False)
    monkeypatch.setattr("core.eva_core.tools.application.shutil.which", lambda _, path=None: "/usr/bin/google-chrome")
    monkeypatch.setattr("core.eva_core.tools.application.subprocess.Popen", lambda *args, **kwargs: pytest.fail("must not launch a duplicate"))
    result = tool.execute({"operation": "open", "application": "chrome"})
    assert result.success
    assert result.data["already_running"] is True
    assert result.data["launched"] is False

def test_application_tool_closes_only_target(monkeypatch):
    tool = ApplicationTool()
    terminated = []
    process = type("Process", (), {
        "info": {"pid": 51, "name": "firefox", "exe": "/usr/bin/firefox"},
        "terminate": lambda self: terminated.append(self.info["pid"]),
        "wait": lambda self, timeout: None,
        "is_running": lambda self: False,
    })()
    monkeypatch.setattr(tool, "_running_processes", lambda executable: [process])
    monkeypatch.setattr("core.eva_core.tools.application.shutil.which", lambda name, path=None: None)
    result = tool.execute({"operation": "close", "application": "firefox"})
    assert result.success
    assert terminated == [51]

def test_application_tool_encodes_browser_search(monkeypatch):
    launched = []
    monkeypatch.setattr("core.eva_core.tools.application.shutil.which", lambda _, path=None: "/usr/bin/firefox")
    monkeypatch.setattr("core.eva_core.tools.application.subprocess.Popen", lambda args, **kwargs: launched.append(args))
    result = ApplicationTool().execute({"operation": "search", "application": "firefox", "query": "Python tutorials & asyncio"})
    assert result.success
    assert launched == [["/usr/bin/firefox", "https://www.google.com/search?q=Python+tutorials+%26+asyncio"]]

def test_application_tool_opens_new_search_tab(monkeypatch):
    launched = []
    monkeypatch.setattr("core.eva_core.tools.application.shutil.which", lambda _, path=None: "/usr/bin/firefox")
    monkeypatch.setattr("core.eva_core.tools.application.subprocess.Popen", lambda args, **kwargs: launched.append(args))
    result = ApplicationTool().execute({"operation": "search", "application": "firefox", "query": "leetcode", "new_tab": True})
    assert result.success
    assert launched == [["/usr/bin/firefox", "--new-tab", "https://www.google.com/search?q=leetcode"]]

def test_application_tool_reports_missing_visible_input_backend(monkeypatch):
    tool = ApplicationTool()
    monkeypatch.setattr(tool, "_resolve_executable", lambda executable: "/usr/bin/gnome-text-editor")
    monkeypatch.setattr(tool, "_input_backend", lambda: None)
    result = tool.execute({"operation": "write_text", "application": "text editor", "text": "Artificial Intelligence"})
    assert not result.success
    assert result.error == "InputBackendUnavailable"

def test_desktop_tool_only_opens_approved_directory(monkeypatch, tmp_path):
    tool = DesktopTool()
    tool.approved_roots = (tmp_path.resolve(),)
    opened = []
    monkeypatch.setattr("core.eva_core.tools.desktop.subprocess.Popen", lambda args, **kwargs: opened.append(args))

    res = tool.execute({"operation": "open_directory", "path": str(tmp_path)})
    assert res.success
    assert os.path.basename(opened[0][0]) == "xdg-open"
    assert opened[0][1] == str(tmp_path.resolve())

    denied = tool.execute({"operation": "open_directory", "path": "/etc"})
    assert not denied.success

def test_desktop_tool_validates_volume(monkeypatch):
    tool = DesktopTool()
    monkeypatch.setattr(tool, "_wpctl", lambda: "/usr/bin/wpctl")

    invalid = tool.execute({"operation": "set_volume", "value": 101})
    assert not invalid.success
    assert invalid.error == "InvalidVolume"

def test_desktop_tool_sets_volume_with_fixed_arguments(monkeypatch):
    tool = DesktopTool()
    commands = []
    monkeypatch.setattr(tool, "_wpctl", lambda: "/usr/bin/wpctl")
    monkeypatch.setattr("core.eva_core.tools.desktop.subprocess.run", lambda command, **kwargs: commands.append(command) or type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})())

    result = tool.execute({"operation": "set_volume", "value": 40})
    assert result.success
    assert commands == [["/usr/bin/wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.40"]]
