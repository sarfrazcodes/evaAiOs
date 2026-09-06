import pytest
import sqlite3
import os
from core.eva_core.task.state import TaskStateManager
from core.eva_core.protocol import TaskStatus, TaskStep

# Override DB path for tests to not corrupt real database
import core.eva_core.task.state as state_module
import core.eva_core.database as db_module
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_eva.db')
db_module.DB_PATH = TEST_DB_PATH
state_module.DB_PATH = TEST_DB_PATH

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup test DB schema
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            intent TEXT,
            status TEXT NOT NULL,
            current_step INTEGER DEFAULT 0,
            total_steps INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            result TEXT,
            error TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_steps (
            step_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            description TEXT NOT NULL,
            dependencies TEXT,
            status TEXT NOT NULL,
            result TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()
    
    yield
    
    # Teardown
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_task_creation():
    manager = TaskStateManager()
    task = manager.create_task("req_123", "complex_task")
    assert task.task_id is not None
    assert task.status == TaskStatus.PLANNING

    retrieved = manager.get_task(task.task_id)
    assert retrieved is not None
    assert retrieved.request_id == "req_123"

def test_save_plan_and_transitions():
    manager = TaskStateManager()
    task = manager.create_task("req_456", "complex_task")
    
    step1 = TaskStep(task_id=task.task_id, sequence=1, description="Step 1")
    manager.save_plan(task.task_id, [step1])
    
    task = manager.get_task(task.task_id)
    assert task.total_steps == 1
    assert len(task.steps) == 1
    assert task.steps[0].description == "Step 1"
    
    # Valid transition
    task = manager.transition_task(task.task_id, TaskStatus.PLANNED)
    assert task.status == TaskStatus.PLANNED
    
    # Setup chain to completion
    manager.transition_task(task.task_id, TaskStatus.READY)
    manager.transition_task(task.task_id, TaskStatus.RUNNING)
    manager.transition_task(task.task_id, TaskStatus.COMPLETED)
    
    with pytest.raises(ValueError, match="Invalid transition"):
        manager.transition_task(task.task_id, TaskStatus.RUNNING)

def test_cancel_task():
    manager = TaskStateManager()
    task = manager.create_task("req_789", "complex_task")
    task = manager.cancel_task(task.task_id)
    assert task.status == TaskStatus.CANCELLED
