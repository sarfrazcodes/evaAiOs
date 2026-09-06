import pytest
import sqlite3
import os
from core.eva_core.task.state import TaskStateManager
from core.eva_core.protocol import TaskStep

import core.eva_core.task.state as state_module
import core.eva_core.database as db_module
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_persist_eva.db')

def setup_db():
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

def test_persistence_across_recreation():
    db_module.DB_PATH = TEST_DB_PATH
    state_module.DB_PATH = TEST_DB_PATH
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    setup_db()
    
    manager = TaskStateManager()
    task = manager.create_task("req_999", "complex_task")
    step = TaskStep(task_id=task.task_id, sequence=1, description="Persisted Step")
    manager.save_plan(task.task_id, [step])
    
    # "Restart" by creating a new manager instance
    manager2 = TaskStateManager()
    retrieved = manager2.get_task(task.task_id)
    
    assert retrieved is not None
    assert retrieved.total_steps == 1
    assert len(retrieved.steps) == 1
    assert retrieved.steps[0].description == "Persisted Step"
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
