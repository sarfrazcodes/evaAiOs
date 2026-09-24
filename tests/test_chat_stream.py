import pytest
import sys
import os
import json
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.eva_core.main import app, intent_engine
from core.eva_core.models_intent import IntentModel
import core.eva_core.database as db_module
import core.eva_core.task.state as state_module

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_chat_stream.db')

@pytest.fixture(autouse=True)
def setup_db():
    db_module.DB_PATH = TEST_DB_PATH
    state_module.DB_PATH = TEST_DB_PATH
    db_module.init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

client = TestClient(app)

class MockEngine:
    async def determine_intent(self, content: str, context_str: str = None) -> IntentModel:
        if content == "ambiguous":
            return IntentModel(intent="ambiguous", confidence=0.0)
        elif content == "plan this":
            return IntentModel(intent="complex_task", confidence=0.9)
        else:
            return IntentModel(intent="conversation", confidence=0.9)

# We must patch the intent engine in main for these tests, or patch the llm provider.
# A simple integration test of the stream NDJSON output:

def test_chat_stream_conversation(monkeypatch):
    monkeypatch.setattr("core.eva_core.main.intent_engine", MockEngine())
    
    # We also need to mock llm_provider.stream_text
    class MockProvider:
        async def stream_text(self, prompt, system=""):
            yield "Hel"
            yield "lo "
            yield "EVA"
            
    monkeypatch.setattr("core.eva_core.main.llm_provider", MockProvider())

    response = client.post("/api/v1/core/chat/stream", json={
        "source": "test",
        "input_type": "text",
        "content": "hello"
    })
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"
    
    # Check lines
    lines = [line for line in response.text.split('\n') if line.strip()]
    
    assert len(lines) == 6
    
    status_thinking = json.loads(lines[0])
    assert status_thinking["type"] == "status"
    assert status_thinking["value"] == "thinking"

    meta = json.loads(lines[1])
    assert meta["type"] == "metadata"
    assert meta["data"]["intent"] == "conversation"
    
    chunk1 = json.loads(lines[2])
    assert chunk1["type"] == "token"
    assert chunk1["content"] == "Hel"
    
    chunk2 = json.loads(lines[3])
    assert chunk2["content"] == "lo "
    
    chunk3 = json.loads(lines[4])
    assert chunk3["content"] == "EVA"

    done = json.loads(lines[5])
    assert done["type"] == "done"

def test_chat_stream_planner(monkeypatch):
    monkeypatch.setattr("core.eva_core.main.intent_engine", MockEngine())
    
    class MockPlanner:
        async def generate_plan(self, task_id, request_content):
            return [{"description": "step 1", "dependencies": []}]
            
    monkeypatch.setattr("core.eva_core.main.planner", MockPlanner())

    response = client.post("/api/v1/core/chat/stream", json={
        "source": "test",
        "input_type": "text",
        "content": "plan this"
    })
    
    assert response.status_code == 200
    
    lines = [line for line in response.text.split('\n') if line.strip()]
    
    status_thinking = json.loads(lines[0])
    assert status_thinking["type"] == "status"

    meta = json.loads(lines[1])
    assert meta["type"] == "metadata"
    assert meta["data"]["intent"] == "complex_task"
    assert "task" in meta["data"]

