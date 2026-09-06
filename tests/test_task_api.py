import pytest
import os
import sqlite3
from fastapi.testclient import TestClient

# Mock the database for tests
import core.eva_core.task.state as state_module
import core.eva_core.database as db_module
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_api_eva.db')
db_module.DB_PATH = TEST_DB_PATH
state_module.DB_PATH = TEST_DB_PATH

from core.eva_core.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
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
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_get_task_api_not_found():
    with TestClient(app) as c:
        response = c.get("/api/v1/core/task/invalid_id")
        assert response.status_code == 404
