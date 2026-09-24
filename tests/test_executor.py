import os
import pytest
from core.eva_core.task.state import TaskStateManager
from core.eva_core.protocol import TaskStep, ActionModel
from core.eva_core.executor.executor import Executor
from core.eva_core.tools.registry import ToolRegistry
from core.eva_core.tools.echo import EchoTool
from core.eva_core.permissions.hook import PermissionHook
from core.eva_core.database import init_db
import core.eva_core.database as db_module
import core.eva_core.task.state as state_module

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_executor.db')

@pytest.fixture
def executor_env():
    db_module.DB_PATH = TEST_DB_PATH
    state_module.DB_PATH = TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    init_db()
    
    state_manager = TaskStateManager()
    registry = ToolRegistry()
    registry.register(EchoTool())
    hook = PermissionHook()
    executor = Executor(state_manager, registry, hook)
    
    yield state_manager, executor
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_executor_success(executor_env):
    state_manager, executor = executor_env
    task = state_manager.create_task("req_1", "complex_task")
    
    step1 = TaskStep(task_id=task.task_id, sequence=1, description="step 1", action=ActionModel(tool="echo", arguments={"text": "hello"}))
    step2 = TaskStep(task_id=task.task_id, sequence=2, description="step 2", dependencies=[step1.step_id], action=ActionModel(tool="echo", arguments={"text": "world"}))
    
    state_manager.save_plan(task.task_id, [step1, step2])
    state_manager.transition_task(task.task_id, "planned")
    
    executor.execute_task(task.task_id)
    
    result_task = state_manager.get_task(task.task_id)
    print("Task status:", result_task.status)
    for s in result_task.steps:
        print(f"Step {s.sequence} status: {s.status}, error: {s.error}")
    assert result_task.status == "completed"
    assert result_task.steps[0].status == "completed"
    assert result_task.steps[1].status == "completed"

def test_executor_missing_action(executor_env):
    state_manager, executor = executor_env
    task = state_manager.create_task("req_2", "complex_task")
    
    step1 = TaskStep(task_id=task.task_id, sequence=1, description="step without action")
    
    state_manager.save_plan(task.task_id, [step1])
    state_manager.transition_task(task.task_id, "planned")
    
    executor.execute_task(task.task_id)
    
    result_task = state_manager.get_task(task.task_id)
    assert result_task.status == "action_resolution_required"
    assert result_task.steps[0].status == "failed"

def test_executor_dependency_failure(executor_env):
    state_manager, executor = executor_env
    task = state_manager.create_task("req_3", "complex_task")
    
    step1 = TaskStep(task_id=task.task_id, sequence=1, description="fail step", action=ActionModel(tool="unknown", arguments={}))
    step2 = TaskStep(task_id=task.task_id, sequence=2, description="blocked step", dependencies=[step1.step_id], action=ActionModel(tool="echo", arguments={}))
    
    state_manager.save_plan(task.task_id, [step1, step2])
    state_manager.transition_task(task.task_id, "planned")
    
    executor.execute_task(task.task_id)
    
    result_task = state_manager.get_task(task.task_id)
    assert result_task.status == "failed"
    assert result_task.steps[0].status == "failed"
    assert result_task.steps[1].status == "blocked"
