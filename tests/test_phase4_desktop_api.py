import pytest
import os
import sys
import tempfile
import sqlite3
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import core.eva_core.database as db_module
from core.eva_core.main import app

db_module.init_db()
client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_db():
    db_module.init_db()
    yield

def test_memories_crud():
    # 1. Create memory
    res = client.post("/api/v1/memories", json={
        "title": "Project EVA Architecture",
        "content": "Modular desktop AI operating system written in Flutter and FastAPI.",
        "category": "Projects",
        "privacy": "public",
        "pinned": True,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Project EVA Architecture"
    assert data["pinned"] is True
    mem_id = data["memory_id"]

    # 2. List memories
    res = client.get("/api/v1/memories")
    assert res.status_code == 200
    mems = res.json()
    assert any(m["memory_id"] == mem_id for m in mems)

    # 3. Update memory
    res = client.put(f"/api/v1/memories/{mem_id}", json={
        "title": "Project EVA Architecture v2",
        "pinned": False,
    })
    assert res.status_code == 200
    assert res.json()["title"] == "Project EVA Architecture v2"
    assert res.json()["pinned"] is False

    # 4. Toggle pin
    res = client.post(f"/api/v1/memories/{mem_id}/pin")
    assert res.status_code == 200
    assert res.json()["pinned"] is True

    # 5. Delete memory
    res = client.delete(f"/api/v1/memories/{mem_id}")
    assert res.status_code == 200
    assert res.json()["deleted"] is True

def test_settings_api():
    res = client.post("/api/v1/settings", json={
        "theme_mode": "dark",
        "accent_color": "sage",
        "density": "comfortable",
    })
    assert res.status_code == 200
    assert res.json()["saved"] is True

    res = client.get("/api/v1/settings")
    assert res.status_code == 200
    settings = res.json()
    assert settings.get("accent_color") == "sage"

def test_apps_api():
    res = client.get("/api/v1/apps")
    assert res.status_code == 200
    apps = res.json()
    assert len(apps) > 0
    app_keys = [a["key"] for a in apps]
    assert "chrome" in app_keys or "firefox" in app_keys or "settings" in app_keys

def test_files_api():
    res = client.get("/api/v1/files/list")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "workspace_root" in data

    # Create test directory and file inside workspace
    res = client.post("/api/v1/files/create", json={
        "path": "test_phase4/hello.txt",
        "content": "Hello EVA OS",
        "is_directory": False,
    })
    assert res.status_code == 200

    # Read back file
    res = client.get("/api/v1/files/read?path=test_phase4/hello.txt")
    assert res.status_code == 200
    assert res.json()["content"] == "Hello EVA OS"
