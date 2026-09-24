import pytest
from core.eva_core.tools.registry import ToolRegistry
from core.eva_core.tools.echo import EchoTool

def test_registry_registration():
    reg = ToolRegistry()
    tool = EchoTool()
    reg.register(tool)
    assert reg.has("echo")
    assert reg.get("echo") == tool

def test_duplicate_registration():
    reg = ToolRegistry()
    reg.register(EchoTool())
    with pytest.raises(ValueError):
        reg.register(EchoTool())

def test_unknown_tool():
    reg = ToolRegistry()
    assert reg.get("nonexistent") is None
    assert not reg.has("nonexistent")

def test_list_tools():
    reg = ToolRegistry()
    reg.register(EchoTool())
    tools = reg.list_tools()
    assert "echo" in tools
