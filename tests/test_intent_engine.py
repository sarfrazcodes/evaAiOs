import pytest
import sys
import os
from typing import Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.eva_core.intent.engine import IntentEngine
from core.eva_core.intent.router import Router
from core.eva_core.models_intent import IntentModel
from core.eva_core.llm.provider import LLMProvider

class MockLLMProvider(LLMProvider):
    def __init__(self, mock_response: Dict[str, Any]):
        self.mock_response = mock_response
        self.last_prompt = ""

    async def generate_json(self, prompt: str, system: str = "") -> Dict[str, Any]:
        self.last_prompt = prompt
        if "error" in self.mock_response:
            raise RuntimeError(self.mock_response["error"])
        return self.mock_response

@pytest.mark.asyncio
async def test_fast_path_conversation():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    
    # Exact match
    intent = await engine.determine_intent("hello")
    assert intent.intent == "conversation"
    
    # Typo / Alias
    intent2 = await engine.determine_intent("helo eva")
    assert intent2.intent == "conversation"

@pytest.mark.asyncio
async def test_fast_path_application():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    
    intent = await engine.determine_intent("open chrome")
    assert intent.intent == "application_operation"
    assert intent.parameters.get("application") == "chrome"
    
    # Typo prefix
    intent2 = await engine.determine_intent("opne vscode")
    assert intent2.intent == "application_operation"
    assert intent2.parameters.get("application") == "vscode"

@pytest.mark.asyncio
async def test_application_lifecycle_and_browser_search_fast_paths():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    close = await engine.determine_intent("close firefox")
    assert close.intent == "application_operation"
    assert close.parameters["operation"] == "close"
    focus = await engine.determine_intent("focus vscode")
    assert focus.parameters["operation"] == "focus"
    search = await engine.determine_intent("search for Python tutorials in firefox")
    assert search.intent == "browser_operation"
    assert search.parameters == {"query": "python tutorials", "application": "firefox"}
    contextual = await engine.determine_intent("close it")
    assert contextual.parameters["application"] == "__context__"

    intent3 = await engine.determine_intent("hey could you open vs code for me")
    assert intent3.intent == "application_operation"
    assert intent3.parameters.get("application") == "vs code"
    assert intent3.parameters.get("new_window") is False

    intent4 = await engine.determine_intent("i want a new window of vs code to be opened")
    assert intent4.intent == "application_operation"
    assert intent4.parameters.get("application") == "vs code"
    assert intent4.parameters.get("new_window") is True

    intent5 = await engine.determine_intent("open settings")
    assert intent5.intent == "application_operation"
    assert intent5.parameters.get("application") == "settings"

    intent6 = await engine.determine_intent("open file explorer")
    assert intent6.intent == "desktop_operation"
    assert intent6.parameters.get("request") == "open file explorer"

    volume = await engine.determine_intent("set volume to 40")
    assert volume.intent == "desktop_control"
    assert volume.parameters == {"operation": "set_volume", "value": 40.0}

    mute = await engine.determine_intent("mute audio")
    assert mute.intent == "desktop_control"
    assert mute.parameters == {"operation": "mute"}

@pytest.mark.asyncio
async def test_fast_path_file_creation():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    intent = await engine.determine_intent("create a folder")
    assert intent.intent == "file_operation"

@pytest.mark.asyncio
async def test_fast_path_browser():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    intent = await engine.determine_intent("search for ai agents")
    assert intent.intent == "browser_operation"

    intent2 = await engine.determine_intent("serach the web for python")
    assert intent2.intent == "browser_operation"
    assert "python" in intent2.parameters.get("query", "")

@pytest.mark.asyncio
async def test_fast_path_document():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    intent = await engine.determine_intent("create a word document")
    assert intent.intent == "document_operation"

@pytest.mark.asyncio
async def test_fast_path_system():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    intent = await engine.determine_intent("check cpu usage")
    assert intent.intent == "system_command"
    
    intent2 = await engine.determine_intent("ss")
    assert intent2.intent == "system_command"

@pytest.mark.asyncio
async def test_llm_fallback_preserves_original_context():
    mock_llm = MockLLMProvider({"intent": "complex_task", "confidence": 0.9})
    engine = IntentEngine(llm_provider=mock_llm)
    
    original_text = "Could you please research AI agents and create a Word report for my project?"
    intent = await engine.determine_intent(original_text)
    
    assert intent.intent == "complex_task"
    assert original_text in mock_llm.last_prompt

@pytest.mark.asyncio
async def test_llm_fallback_invalid_intent():
    mock_resp = {
        "intent": "made_up_intent",
        "confidence": 0.9,
    }
    engine = IntentEngine(llm_provider=MockLLMProvider(mock_resp))
    intent = await engine.determine_intent("do something weird")
    assert intent.intent == "ambiguous" # defaults to ambiguous

@pytest.mark.asyncio
async def test_llm_provider_error_handling():
    mock_resp = {"error": "Connection refused"}
    engine = IntentEngine(llm_provider=MockLLMProvider(mock_resp))
    intent = await engine.determine_intent("help")
    assert intent.intent == "ambiguous"
    assert intent.confidence == 0.0
    assert "Connection refused" in intent.reason

def test_router():
    router = Router()
    
    intent1 = IntentModel(intent="application_operation", confidence=0.9)
    route1 = router.route(intent1)
    assert route1.route == "application"

    intent2 = IntentModel(intent="complex_task", confidence=0.8)
    route2 = router.route(intent2)
    assert route2.route == "planner"
    
    # Low confidence test
    intent3 = IntentModel(intent="file_operation", confidence=0.4)
    route3 = router.route(intent3)
    assert route3.route == "clarification"
