import asyncio
import os
import shutil
import sqlite3
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import core.eva_core.database as db_module
import core.eva_core.task.state as state_module
from core.eva_core.database import init_db
from core.eva_core.protocol import ActionModel, RequestModel, TaskStatus, TaskStep
from core.eva_core.llm.gemini_provider import GeminiProvider
from core.eva_core.llm.model_router import ModelRouter, PrivacyMode
from core.eva_core.tools.file import FileTool, WORKSPACE_ROOT
from core.eva_core.tools.registry import ToolRegistry
from core.eva_core.tools.desktop import DesktopTool
from core.eva_core.permissions.hook import PermissionHook
from core.eva_core.executor.executor import Executor
from core.eva_core.task.state import TaskStateManager
from core.eva_core.task.queue import TaskQueue
from core.eva_core.task.events import TaskEventManager
from core.eva_core.task.recovery import RecoveryManager
from core.eva_core.task.worker import ExecutionWorker
from core.eva_core.task.agent_session import AgentSession, SessionManager
from core.eva_core.stt.agentic_voice import AgenticVoiceService
from core.eva_core.intent.matcher import IntentMatcher
from core.eva_core.main import handle_request, _resolve_contextual_file_and_directory, approve_confirmation_endpoint

TEST_DB = os.path.join(os.path.dirname(__file__), "test_agentic_v2.db")

@pytest.fixture(autouse=True)
def setup_test_db():
    orig_db = db_module.DB_PATH
    orig_state = state_module.DB_PATH
    db_module.DB_PATH = TEST_DB
    state_module.DB_PATH = TEST_DB
    init_db()
    yield
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass
    db_module.DB_PATH = orig_db
    state_module.DB_PATH = orig_state


# ── 1. Phase 2: Public / Private AI Router Tests ──────────────────────────────

@pytest.mark.asyncio
async def test_gemini_provider_mocked():
    provider = GeminiProvider(api_key="fake-test-key")
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": '{"result": "mocked success"}'}]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        res = await provider.generate_json("Hello Gemini")
        assert res == {"result": "mocked success"}

@pytest.mark.asyncio
async def test_model_router_modes():
    router = ModelRouter()
    # Test Private mode: local only
    router.set_privacy_mode(PrivacyMode.PRIVATE)
    provider, target, reason = router.route_provider(requires_complex_reasoning=True, contains_private_data=True)
    assert target == "ollama"

    # Test Hybrid mode with private data: routed to local
    router.set_privacy_mode(PrivacyMode.HYBRID)
    provider, target, reason = router.route_provider(requires_complex_reasoning=True, contains_private_data=True)
    assert target == "ollama"

    # Test Public mode with configured Gemini
    router.set_privacy_mode(PrivacyMode.PUBLIC)
    with patch.object(router.gemini, "is_configured", return_value=True):
        provider, target, reason = router.route_provider(requires_complex_reasoning=True, contains_private_data=False)
        assert target == "gemini"


# ── 2. Phase 6: Expanded File Tool Operations ─────────────────────────────────

def test_file_tool_expanded_operations():
    tool = FileTool()
    test_dir = "test_expansion_dir"
    test_file = f"{test_dir}/code.py"

    # 1. Create directory
    res = tool.execute({"operation": "create_directory", "path": test_dir})
    assert res.success is True

    # 2. Create file
    res = tool.execute({"operation": "create_file", "path": test_file, "content": "print('hello world')\n"})
    assert res.success is True

    # 3. File Info
    info_res = tool.execute({"operation": "file_info", "path": test_file})
    assert info_res.success is True
    assert info_res.data["is_file"] is True
    assert info_res.data["line_count"] == 1

    # 4. Append File
    append_res = tool.execute({"operation": "append_file", "path": test_file, "content": "print('second line')\n"})
    assert append_res.success is True
    assert append_res.data["lines"] == 2

    # 5. Edit File (targeted replacement)
    edit_res = tool.execute({
        "operation": "edit_file",
        "path": test_file,
        "target": "hello world",
        "replacement": "eva ai os"
    })
    assert edit_res.success is True

    # 6. Verify edit with read_file
    read_res = tool.execute({"operation": "read_file", "path": test_file})
    assert "eva ai os" in read_res.data["content"]

    # 7. Search files
    search_res = tool.execute({"operation": "search_files", "path": test_dir, "query": "eva"})
    assert search_res.success is True
    assert search_res.data["count"] >= 1

    # Clean up test dir inside WORKSPACE_ROOT
    shutil.rmtree(os.path.join(WORKSPACE_ROOT, test_dir), ignore_errors=True)


# ── 3. Phase 4: Contextual Multi-Turn Execution ───────────────────────────────

@pytest.mark.asyncio
async def test_contextual_multi_turn_flow():
    """Tests the exact user flow:
    1. Create folder called DSA
    2. Inside it create dfs.cpp
    3. Implement DFS in C++
    4. Add comments
    """
    session_id = "test_multi_turn_session"
    matcher = IntentMatcher()

    # Step 1: Create a folder called DSA
    req1 = matcher.match("create a folder called DSA")
    assert req1 is not None
    assert req1.parameters["operation"] == "create_directory"
    assert req1.parameters["path"].lower() == "dsa"

    def approve_if_needed(res):
        if res.status == "requires_confirmation" and res.data and "task" in res.data:
            task_info = res.data["task"]
            conf_id = task_info["steps"][0]["error"]["details"]["confirmation_id"]
            approved_res = approve_confirmation_endpoint(conf_id)
            assert approved_res["confirmation"]["status"] in {"approved", "executed"}

    res1 = await handle_request(RequestModel(
        source="test",
        input_type="text",
        content="create a folder called DSA",
        session_id=session_id
    ))
    approve_if_needed(res1)

    # Verify session active directory
    session = SessionManager().get_or_create(session_id)
    assert session.active_directory.lower() == "dsa"

    # Step 2: Inside it create dfs.cpp
    req2 = matcher.match("inside it create dfs.cpp")
    assert req2 is not None
    req2 = _resolve_contextual_file_and_directory(req2, session_id)
    assert req2.parameters["path"].lower() == "dsa/dfs.cpp"

    res2 = await handle_request(RequestModel(
        source="test",
        input_type="text",
        content="inside it create dfs.cpp",
        session_id=session_id
    ))
    approve_if_needed(res2)
    assert session.active_file.lower() == "dsa/dfs.cpp"

    # Step 3: Implement DFS in C++
    req3 = matcher.match("implement DFS in C++")
    assert req3 is not None
    req3 = _resolve_contextual_file_and_directory(req3, session_id)
    assert req3.parameters["path"].lower() == "dsa/dfs.cpp"

    res3 = await handle_request(RequestModel(
        source="test",
        input_type="text",
        content="implement DFS in C++",
        session_id=session_id
    ))
    approve_if_needed(res3)

    # Verify file was generated with C++ DFS
    ft = FileTool()
    file_content = ft.execute({"operation": "read_file", "path": "dsa/dfs.cpp"}).data["content"]
    assert "void dfs" in file_content

    # Step 4: Add comments
    req4 = matcher.match("add explanatory comments")
    assert req4 is not None
    req4 = _resolve_contextual_file_and_directory(req4, session_id)
    assert req4.parameters["path"].lower() == "dsa/dfs.cpp"

    res4 = await handle_request(RequestModel(
        source="test",
        input_type="text",
        content="add explanatory comments",
        session_id=session_id
    ))
    approve_if_needed(res4)

    updated_content = ft.execute({"operation": "read_file", "path": "dsa/dfs.cpp"}).data["content"]
    assert "Depth First Search" in updated_content

    # Cleanup
    shutil.rmtree(os.path.join(WORKSPACE_ROOT, "dsa"), ignore_errors=True)


# ── 4. Phase 5: Persistent Agent Execution Engine ─────────────────────────────

def test_persistent_execution_and_events():
    state_mgr = TaskStateManager()
    event_mgr = TaskEventManager()
    queue = TaskQueue()

    tool_reg = ToolRegistry()
    tool_reg.register(FileTool())
    tool_reg.register(DesktopTool())
    hook = PermissionHook()
    exec_engine = Executor(state_manager=state_mgr, tool_registry=tool_reg, permission_hook=hook)

    worker = ExecutionWorker(
        queue=queue,
        state_manager=state_mgr,
        executor=exec_engine,
        event_manager=event_mgr
    )

    # Create a persistent task
    task = state_mgr.create_task("req-worker-1", "test_background_worker")
    step = TaskStep(
        task_id=task.task_id,
        sequence=1,
        description="Check desktop emergency stop",
        action=ActionModel(tool="desktop_tool", arguments={"operation": "emergency_stop"})
    )
    state_mgr.save_plan(task.task_id, [step])
    state_mgr.transition_task(task.task_id, TaskStatus.PLANNED)

    # Subscribe to events
    history_before = event_mgr.get_history(task.task_id)
    assert isinstance(history_before, list)

    # Enqueue task
    assert queue.enqueue(task.task_id, priority=1) is True
    assert queue.contains(task.task_id) is True

    # Run single execution directly via worker
    control = worker.get_control(task.task_id)
    worker._execute_single_task(task.task_id, None, control)

    # Verify task completed in database
    retrieved = state_mgr.get_task(task.task_id)
    assert retrieved.status == TaskStatus.COMPLETED

    # Verify events recorded in history replay buffer
    history_after = event_mgr.get_history(task.task_id)
    event_types = [e["event_type"] for e in history_after]
    assert "task_started" in event_types
    assert "task_completed" in event_types


def test_recovery_manager():
    state_mgr = TaskStateManager()
    event_mgr = TaskEventManager()
    recovery = RecoveryManager(state_manager=state_mgr, event_manager=event_mgr)

    # Create a simulated interrupted task (e.g. server crash during execution)
    task = state_mgr.create_task("req-crash", "interrupted_task")
    step1 = TaskStep(task_id=task.task_id, sequence=1, description="Step 1 Completed", status="completed")
    step2 = TaskStep(task_id=task.task_id, sequence=2, description="Step 2 Interrupted", status="running")
    state_mgr.save_plan(task.task_id, [step1, step2])
    state_mgr.transition_task(task.task_id, TaskStatus.PLANNED)
    state_mgr.transition_task(task.task_id, TaskStatus.READY)
    state_mgr.claim_execution(task.task_id)

    # Recover
    recovered = recovery.recover_interrupted_tasks()
    assert any(r["task_id"] == task.task_id for r in recovered)

    recovered_task = state_mgr.get_task(task.task_id)
    assert recovered_task.status in {TaskStatus.READY, TaskStatus.PLANNED}
    # Crucial: completed step 1 was NOT restarted
    assert recovered_task.steps[0].status == "completed"
    # Interrupted step 2 was reset to pending safely
    assert recovered_task.steps[1].status == "pending"


# ── 5. Phase 3: Agentic Voice Service Control ─────────────────────────────────

def test_agentic_voice_service_lifecycle():
    service = AgenticVoiceService()
    status = service.status()
    assert "active" in status
    assert "listening" in status

    # Test emergency stop halts playback and pauses
    emerg = service.emergency_stop()
    assert emerg["paused"] is True
    assert emerg["listening"] is False

    # Test resume
    res = service.resume()
    assert res["paused"] is False
