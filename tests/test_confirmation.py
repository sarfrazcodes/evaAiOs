import os
import sqlite3
import threading
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from core.eva_core.protocol import ActionModel, TaskStep, ToolResult, TaskStatus, utc_now
from core.eva_core.task.state import TaskStateManager
import core.eva_core.database as db_module
import core.eva_core.task.state as state_module
from core.eva_core.permissions.hook import PermissionHook, PermissionDecision
from core.eva_core.executor.executor import Executor
from core.eva_core.tools.file import FileTool
from core.eva_core.tools.registry import ToolRegistry
from core.eva_core.main import app, executor as app_executor, state_manager as app_state_manager

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_confirmation.db")
client = TestClient(app)


@pytest.fixture(autouse=True)
def confirmation_db(monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", TEST_DB_PATH)
    monkeypatch.setattr(state_module, "DB_PATH", TEST_DB_PATH)
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    assert db_module.init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def make_blocked_task():
    manager = TaskStateManager()
    registry = ToolRegistry()
    registry.register(FileTool())
    hook = PermissionHook()
    task = manager.create_task("confirmation-request", "file_operation")
    step = TaskStep(
        task_id=task.task_id,
        sequence=1,
        description="Create a file",
        action=ActionModel(tool="file_tool", arguments={"operation": "create_file", "path": "confirmation.txt", "content": "ok"}),
    )
    manager.save_plan(task.task_id, [step])
    manager.transition_task(task.task_id, TaskStatus.PLANNED)
    Executor(manager, registry, hook).execute_task(task.task_id)
    return manager, task.task_id


def test_confirmation_creation_and_retrieval():
    manager, task_id = make_blocked_task()
    task = manager.get_task(task_id)
    details = task.steps[0].error.details
    confirmation = manager.get_confirmation(details["confirmation_id"])
    assert task.status == TaskStatus.BLOCKED
    assert confirmation["task_id"] == task_id
    assert confirmation["tool_name"] == "file_tool"
    assert confirmation["arguments"]["path"] == "confirmation.txt"
    assert confirmation["status"] == "pending"
    assert confirmation["request_id"] == "confirmation-request"


def test_natural_language_request_creates_confirmation():
    response = client.post("/api/v1/core/request", json={
        "source": "desktop",
        "input_type": "text",
        "content": "create a file called apiconfirmationtxt",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "requires_confirmation"
    task = body["data"]["task"]
    details = task["steps"][0]["error"]["details"]
    confirmation = client.get(f"/api/v1/core/confirmation/{details['confirmation_id']}")
    assert confirmation.status_code == 200
    assert confirmation.json()["arguments"]["path"] == "apiconfirmationtxt"


def test_api_approve_executes_exact_operation(monkeypatch):
    manager, task_id = make_blocked_task()
    confirmation_id = manager.get_task(task_id).steps[0].error.details["confirmation_id"]
    calls = []

    def fake_execute(self, arguments):
        calls.append(dict(arguments))
        return ToolResult(success=True, tool_name=self.name, message="created")

    monkeypatch.setattr(FileTool, "execute", fake_execute)
    response = client.post(f"/api/v1/core/confirmation/{confirmation_id}/approve")
    assert response.status_code == 200
    assert response.json()["confirmation"]["status"] == "executed"
    assert response.json()["task"]["status"] == "completed"
    assert calls == [{"operation": "create_file", "path": "confirmation.txt", "content": "ok"}]

    duplicate = client.post(f"/api/v1/core/confirmation/{confirmation_id}/approve")
    assert duplicate.status_code == 409
    assert len(calls) == 1


def test_api_deny_cancels_without_execution(monkeypatch):
    manager, task_id = make_blocked_task()
    confirmation_id = manager.get_task(task_id).steps[0].error.details["confirmation_id"]
    monkeypatch.setattr(FileTool, "execute", lambda self, arguments: pytest.fail("denied operation executed"))
    response = client.post(f"/api/v1/core/confirmation/{confirmation_id}/deny")
    assert response.status_code == 200
    assert response.json()["confirmation"]["status"] == "denied"
    assert response.json()["task"]["status"] == "cancelled"


def test_unknown_and_expired_confirmation_are_rejected():
    missing = client.get("/api/v1/core/confirmation/does-not-exist")
    assert missing.status_code == 404
    manager, task_id = make_blocked_task()
    confirmation_id = manager.get_task(task_id).steps[0].error.details["confirmation_id"]
    with sqlite3.connect(TEST_DB_PATH) as conn:
        conn.execute("UPDATE confirmations SET expires_at = ? WHERE confirmation_id = ?", ((utc_now() - timedelta(seconds=1)).isoformat(), confirmation_id))
        conn.commit()
    expired = client.post(f"/api/v1/core/confirmation/{confirmation_id}/approve")
    assert expired.status_code == 409
    assert manager.get_confirmation(confirmation_id)["status"] == "expired"


def test_blocked_tool_cannot_be_approved():
    manager, task_id = make_blocked_task()
    confirmation_id = manager.get_task(task_id).steps[0].error.details["confirmation_id"]
    with sqlite3.connect(TEST_DB_PATH) as conn:
        conn.execute("UPDATE confirmations SET tool_name = 'shell_tool' WHERE confirmation_id = ?", (confirmation_id,))
        conn.commit()
    response = client.post(f"/api/v1/core/confirmation/{confirmation_id}/approve")
    assert response.status_code == 403
    assert manager.get_confirmation(confirmation_id)["status"] == "pending"


def test_pending_confirmation_survives_state_manager_restart():
    manager, task_id = make_blocked_task()
    confirmation_id = manager.get_task(task_id).steps[0].error.details["confirmation_id"]
    restarted_manager = TaskStateManager()
    recovered = restarted_manager.get_confirmation(confirmation_id)
    assert recovered["status"] == "pending"
    assert recovered["task_id"] == task_id


def test_confirmation_cannot_be_tampered_or_reused():
    manager, task_id = make_blocked_task()
    confirmation_id = manager.get_task(task_id).steps[0].error.details["confirmation_id"]
    confirmation = manager.get_confirmation(confirmation_id)
    assert manager.consume_confirmation(confirmation_id, task_id, confirmation["step_id"], "file_tool", {"operation": "create_file", "path": "other.txt", "content": "ok"}) is False
    assert manager.transition_confirmation(confirmation_id, "approved")["status"] == "approved"
    assert manager.consume_confirmation(confirmation_id, task_id, confirmation["step_id"], confirmation["tool_name"], confirmation["arguments"]) is True
    assert manager.consume_confirmation(confirmation_id, task_id, confirmation["step_id"], confirmation["tool_name"], confirmation["arguments"]) is False


def test_concurrent_approval_only_one_wins():
    manager, task_id = make_blocked_task()
    confirmation_id = manager.get_task(task_id).steps[0].error.details["confirmation_id"]
    results = []

    def approve():
        results.append(manager.transition_confirmation(confirmation_id, "approved").get("transitioned", False))

    threads = [threading.Thread(target=approve) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count(True) == 1
    assert results.count(False) == 1
