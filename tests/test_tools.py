import os
import pytest
from core.eva_core.tools.echo import EchoTool
from core.eva_core.tools.calculator import CalculatorTool
from core.eva_core.tools.file import FileTool, WORKSPACE_ROOT
from core.eva_core.tools.application import ApplicationTool

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

def test_application_tool():
    tool = ApplicationTool()
    res = tool.execute({"operation": "open", "application": "chrome"})
    assert res.success
    
    res_fail = tool.execute({"operation": "open", "application": "malware"})
    assert not res_fail.success
    assert res_fail.error == "UnauthorizedApplication"
