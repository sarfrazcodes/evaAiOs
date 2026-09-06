import pytest
import sys
import os
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.eva_core.intent.engine import IntentEngine
from core.eva_core.intent.router import Router
from core.eva_core.models_intent import IntentModel
from core.eva_core.llm.provider import LLMProvider

class MockLLMProvider(LLMProvider):
    def __init__(self, mock_response: Dict[str, Any]):
        self.mock_response = mock_response

    async def generate_json(self, prompt: str, system: str = "") -> Dict[str, Any]:
        if "error" in self.mock_response:
            raise RuntimeError(self.mock_response["error"])
        return self.mock_response

@pytest.mark.asyncio
async def test_fast_path_conversation():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    intent = await engine.determine_intent("hello eva")
    assert intent.intent == "conversation"
    assert intent.confidence == 1.0

@pytest.mark.asyncio
async def test_fast_path_application():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    intent = await engine.determine_intent("open chrome")
    assert intent.intent == "application_operation"
    assert intent.confidence == 1.0
    assert intent.parameters.get("application") == "chrome"

@pytest.mark.asyncio
async def test_fast_path_file_creation():
    engine = IntentEngine(llm_provider=MockLLMProvider({}))
    intent = await engine.determine_intent("create a folder called projects")
    assert intent.intent == "file_operation"
    assert intent.confidence == 1.0
    assert intent.parameters.get("operation") == "create_directory"
    assert intent.parameters.get("name") == "projects"

@pytest.mark.asyncio
async def test_llm_fallback_complex_task():
    mock_resp = {
        "intent": "complex_task",
        "confidence": 0.95,
        "reason": "Requires multiple steps",
        "parameters": {}
    }
    engine = IntentEngine(llm_provider=MockLLMProvider(mock_resp))
    intent = await engine.determine_intent("research AI agents and create a report")
    assert intent.intent == "complex_task"
    assert intent.confidence == 0.95

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
