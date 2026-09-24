import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.eva_core.main import app, state_manager
from core.eva_core.protocol import TaskStep, ActionModel
import core.eva_core.database as db_module
import core.eva_core.task.state as state_module

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_integration.db')

@pytest.fixture(autouse=True)
def setup_db():
    # Patch DB paths before each test
    db_module.DB_PATH = TEST_DB_PATH
    state_module.DB_PATH = TEST_DB_PATH
    db_module.init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

client = TestClient(app)

def test_hello_eva():
    response = client.post("/api/v1/core/request", json={
        "source": "desktop",
        "input_type": "text",
        "content": "hello eva!"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["intent"] == "conversation"
    assert data["data"]["route"] == "conversation"

def test_open_chrome():
    response = client.post("/api/v1/core/request", json={
        "source": "desktop",
        "input_type": "text",
        "content": "open chrome"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["intent"] == "application_operation"
    assert data["data"]["route"] == "application"

def test_create_folder():
    response = client.post("/api/v1/core/request", json={
        "source": "desktop",
        "input_type": "text",
        "content": "create a folder called projects"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["intent"] == "file_operation"
    assert data["data"]["route"] == "file"

def test_complex_task_ollama_unavailable():
    # If Ollama is unavailable, the fallback LLM call will throw an exception
    # IntentEngine gracefully handles it returning ambiguous with 0 confidence
    from core.eva_core.models_intent import IntentModel
    with patch('core.eva_core.intent.engine.IntentEngine._evaluate_llm', side_effect=Exception("Ollama down")):
        response = client.post("/api/v1/core/request", json={
            "source": "desktop",
            "input_type": "text",
            "content": "research AI agents and create a Word report"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "requires_confirmation"
        assert data["data"]["intent"] == "ambiguous"
        assert data["data"]["confidence"] == 0.0
        assert data["data"]["route"] == "clarification"

def test_complex_task_planner_unavailable():
    # If the Intent matches complex_task but planner fails (e.g. Ollama down during planning)
    from core.eva_core.models_intent import IntentModel
    mock_intent = IntentModel(intent="complex_task", confidence=0.9, parameters={})
    with patch('core.eva_core.intent.engine.IntentEngine._evaluate_llm', return_value=mock_intent):
        with patch('core.eva_core.task.planner.Planner.generate_plan', side_effect=Exception("Ollama down")):
            response = client.post("/api/v1/core/request", json={
                "source": "desktop",
                "input_type": "text",
                "content": "research AI agents and create a Word report"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "requires_confirmation"
            assert "task" in data["data"]
            assert data["data"]["task"]["status"] == "requires_clarification"

def test_execution_e2e_deterministic():
    # Manually insert a planned task into state manager to mock planner output
    task = state_manager.create_task("integration_req_1", "complex_task")
    step1 = TaskStep(task_id=task.task_id, sequence=1, description="step 1", action=ActionModel(tool="echo", arguments={"text": "hello"}))
    step2 = TaskStep(task_id=task.task_id, sequence=2, description="step 2", dependencies=[step1.step_id], action=ActionModel(tool="calculator", arguments={"operation": "add", "a": 5, "b": 3}))
    
    state_manager.save_plan(task.task_id, [step1, step2])
    state_manager.transition_task(task.task_id, "planned")
    
    response = client.post(f"/api/v1/core/task/{task.task_id}/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["status"] == "completed"
    assert data["steps"][1]["status"] == "completed"

def test_execution_e2e_missing_action():
    # Mocks Planner returning steps without structured action 
    task = state_manager.create_task("integration_req_2", "complex_task")
    step1 = TaskStep(task_id=task.task_id, sequence=1, description="natural language step without action")
    
    state_manager.save_plan(task.task_id, [step1])
    state_manager.transition_task(task.task_id, "planned")
    
    response = client.post(f"/api/v1/core/task/{task.task_id}/execute")
    assert response.status_code == 200
    data = response.json()
    # Safely fails without LLM resolving tool
    assert data["status"] == "action_resolution_required"
    assert data["steps"][0]["status"] == "failed"
