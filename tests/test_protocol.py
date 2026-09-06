import sys
import os
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.eva_core.protocol import RequestModel, ResponseModel, TaskModel, ActionModel
from core.eva_core.main import app

client = TestClient(app)

def test_request_model_creation():
    req = RequestModel(source="test", input_type="text", content="hello")
    assert req.request_id is not None
    assert req.source == "test"
    assert req.content == "hello"
    assert req.timestamp.tzinfo == timezone.utc

def test_invalid_request_model():
    with pytest.raises(ValidationError):
        # Missing required fields
        RequestModel(content="hello")

def test_response_model():
    resp = ResponseModel(request_id="123", status="accepted", message="ok")
    assert resp.request_id == "123"
    assert resp.status == "accepted"
    assert resp.error is None

def test_task_model():
    task = TaskModel(request_id="req-123", status="pending")
    assert task.task_id is not None
    assert task.current_step == 0
    assert task.total_steps == 0

def test_action_model():
    action = ActionModel(tool="test_tool", arguments={"key": "value"})
    assert action.tool == "test_tool"
    assert action.arguments["key"] == "value"

def test_api_core_request():
    payload = {
        "source": "pytest",
        "input_type": "text",
        "content": "Open Chrome"
    }
    response = client.post("/api/v1/core/request", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "request_id" in data
    assert "application_operation" in data["message"]

def test_api_core_request_invalid():
    payload = {
        "source": "pytest"
        # missing input_type and content
    }
    response = client.post("/api/v1/core/request", json=payload)
    assert response.status_code == 422 # Validation Error
