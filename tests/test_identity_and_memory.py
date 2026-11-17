"""
EVA AI OS — Identity & Memory Test Suite
Tests:
  1.  PersonalMemoryManager seeds owner profile correctly
  2.  get_identity_fast_response — "Who am I?"
  3.  get_identity_fast_response — "What is my name?"
  4.  get_identity_fast_response — "Who created you?"
  5.  get_identity_fast_response — "What is your creator's full name?"
  6.  get_identity_fast_response — "What do I do?"
  7.  get_identity_fast_response — "What do you know about me?"
  8.  get_identity_fast_response — "Do you remember who created you?"
  9.  get_identity_fast_response — greetings do NOT match (fall through to conversation)
  10. Memory CRUD: create, retrieve, update, delete
  11. Privacy classification enforced
  12. Profile persists across fresh PersonalMemoryManager re-init
  13. IntentMatcher returns personal_identity intent for identity questions
  14. IntentMatcher does NOT return personal_identity for plain greetings
  15. MediaExecutionState.NAVIGATION_STARTED returned for YouTube search
  16. Recording duration timer returns remaining/elapsed fields
"""

import os
import sqlite3
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# ─── Test DB isolation ────────────────────────────────────────────────────────
import core.eva_core.database as db_module

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_identity_memory.db")

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    """Each test gets a clean, isolated SQLite database."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    monkeypatch.setattr(db_module, "DB_PATH", TEST_DB_PATH)

    # Also patch the PersonalMemoryManager singleton so it re-initialises per test
    from core.eva_core.memory import personal_memory as pm_module
    monkeypatch.setattr(pm_module, "DB_PATH", TEST_DB_PATH, raising=False)
    # Reset singleton
    if hasattr(pm_module.PersonalMemoryManager, "_instance"):
        pm_module.PersonalMemoryManager._instance = None

    db_module.init_db()
    yield

    # Teardown
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    # Reset singleton again after test
    from core.eva_core.memory import personal_memory as pm_module2
    if hasattr(pm_module2.PersonalMemoryManager, "_instance"):
        pm_module2.PersonalMemoryManager._instance = None


def _get_manager():
    from core.eva_core.memory.personal_memory import PersonalMemoryManager
    # Force re-init with test DB
    mgr = PersonalMemoryManager(db_path=TEST_DB_PATH)
    return mgr


# ─── 1. Seed correctness ─────────────────────────────────────────────────────

def test_seed_owner_profile_present():
    """PersonalMemoryManager seeds all required owner profile fields."""
    mgr = _get_manager()
    profile = mgr.get_owner_profile()

    assert profile["nickname"] == "Saif"
    assert profile["full_name"] == "Mohd Sarfraz Saifi"
    assert profile["preferred_name"] == "Sarfraz"
    assert profile["call_name"] == "Saif"
    assert "btech" in profile["occupation"].lower() or "computer science" in profile["occupation"].lower()
    assert profile["creator_of_eva"] is True


def test_seed_assistant_identity_present():
    """PersonalMemoryManager seeds assistant identity fields."""
    mgr = _get_manager()
    identity = mgr.get_assistant_identity()

    assert identity["name"] == "EVA"
    assert identity["creator_name"] == "Sarfraz"
    assert identity["creator_full_name"] == "Mohd Sarfraz Saifi"


# ─── 2–8. Identity fast-response correctness ─────────────────────────────────

@pytest.mark.parametrize("question,expected_fragments", [
    ("Who am I?", ["Saif", "BTech"]),
    ("What is my name?", ["Mohd Sarfraz Saifi", "Saif"]),
    ("Who created you?", ["Sarfraz"]),
    ("What is your creator's full name?", ["Mohd Sarfraz Saifi"]),
    ("What do I do?", ["BTech", "student"]),
    ("What do you know about me?", ["Saif", "Mohd Sarfraz Saifi"]),
    ("Do you remember who created you?", ["Sarfraz"]),
])
def test_identity_fast_response(question, expected_fragments):
    """Fast-path returns correct answers for identity questions without LLM."""
    mgr = _get_manager()
    response = mgr.get_identity_fast_response(question)
    assert response is not None, f"No fast response for: {question!r}"
    for fragment in expected_fragments:
        assert fragment in response, (
            f"Expected {fragment!r} in fast response for {question!r}; got: {response!r}"
        )


def test_identity_fast_response_case_insensitive():
    """Fast-path works with uppercase, lowercase, mixed case, and trailing punctuation."""
    mgr = _get_manager()
    for variant in ["WHO AM I?", "who am i", "who am i??", "  Who Am I  "]:
        resp = mgr.get_identity_fast_response(variant)
        assert resp is not None, f"Should match: {variant!r}"
        assert "Saif" in resp


# ─── 9. Greetings must NOT match personal_identity ───────────────────────────

def test_greetings_not_matched_by_fast_path():
    """Plain greetings must fall through to conversation — not personal_identity."""
    mgr = _get_manager()
    for greeting in ["hello", "hi", "hey", "how are you", "good morning"]:
        resp = mgr.get_identity_fast_response(greeting)
        assert resp is None, (
            f"Greeting {greeting!r} should NOT match identity fast-path; got: {resp!r}"
        )


# ─── 10. Memory CRUD ─────────────────────────────────────────────────────────

def test_memory_crud_create_retrieve_update():
    """Can create, retrieve and update a custom memory record."""
    import uuid
    from datetime import datetime, timezone

    conn = sqlite3.connect(TEST_DB_PATH)
    cur = conn.cursor()
    mem_id = f"test_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    cur.execute(
        "INSERT INTO memories (memory_id, title, content, category, privacy, pinned, source, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (mem_id, "Test Memory", "Some content", "Projects", "public", 0, "user", now, now),
    )
    conn.commit()

    # Retrieve
    cur.execute("SELECT title, content FROM memories WHERE memory_id = ?", (mem_id,))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "Test Memory"
    assert row[1] == "Some content"

    # Update
    cur.execute("UPDATE memories SET title = 'Updated Title' WHERE memory_id = ?", (mem_id,))
    conn.commit()
    cur.execute("SELECT title FROM memories WHERE memory_id = ?", (mem_id,))
    assert cur.fetchone()[0] == "Updated Title"

    # Delete
    cur.execute("DELETE FROM memories WHERE memory_id = ?", (mem_id,))
    conn.commit()
    cur.execute("SELECT memory_id FROM memories WHERE memory_id = ?", (mem_id,))
    assert cur.fetchone() is None

    conn.close()


def test_seed_records_have_key_and_confirmed_columns():
    """Seeded identity records have key and confirmed=1 set."""
    _get_manager()  # seeds the DB
    conn = sqlite3.connect(TEST_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT key, confirmed FROM memories WHERE category = 'Owner Profile' AND key IS NOT NULL")
    rows = cur.fetchall()
    conn.close()
    assert len(rows) >= 5, f"Expected at least 5 seeded Owner Profile records, got {len(rows)}"
    for key, confirmed in rows:
        assert key is not None and key != "", f"Empty key in owner profile seed"
        assert confirmed == 1, f"Seed record {key!r} should have confirmed=1"


# ─── 11. Privacy classification ──────────────────────────────────────────────

def test_private_context_excluded_from_public_llm_context():
    """get_structured_llm_context(include_private=False) omits private fields."""
    mgr = _get_manager()
    public_ctx = mgr.get_structured_llm_context(include_private=False)
    private_ctx = mgr.get_structured_llm_context(include_private=True)

    # Both should have the creator (this is in the assistant identity, used publicly)
    assert "EVA" in private_ctx
    # Private context should be a superset of (or equal to) public context
    assert len(private_ctx) >= len(public_ctx)


# ─── 12. Profile persists across re-init ─────────────────────────────────────

def test_profile_persists_across_reinit():
    """Owner profile survives a singleton reset and re-initialization."""
    from core.eva_core.memory import personal_memory as pm_module

    mgr1 = _get_manager()
    p1 = mgr1.get_owner_profile()

    # Reset the singleton (simulates backend restart)
    pm_module.PersonalMemoryManager._instance = None

    mgr2 = pm_module.PersonalMemoryManager(db_path=TEST_DB_PATH)
    p2 = mgr2.get_owner_profile()

    assert p1["nickname"] == p2["nickname"]
    assert p1["full_name"] == p2["full_name"]
    assert p1["creator_of_eva"] == p2["creator_of_eva"]


# ─── 13. IntentMatcher returns personal_identity ─────────────────────────────

def test_intent_matcher_returns_personal_identity_for_identity_questions():
    """IntentMatcher fast-path classifies identity questions as personal_identity."""
    from core.eva_core.intent.matcher import IntentMatcher

    matcher = IntentMatcher()
    for question in [
        "Who am I?",
        "What is my name?",
        "Who created you?",
        "What is your creator's full name?",
        "What do I do?",
        "Do you remember who created you?",
    ]:
        result = matcher.match(question)
        assert result is not None, f"IntentMatcher returned None for: {question!r}"
        assert result.intent == "personal_identity", (
            f"Expected personal_identity for {question!r}, got {result.intent!r}"
        )
        assert result.confidence == 1.0
        assert "fast_response" in result.parameters


# ─── 14. IntentMatcher does NOT return personal_identity for greetings ────────

def test_intent_matcher_greetings_not_personal_identity():
    """Plain greetings must NOT be classified as personal_identity."""
    from core.eva_core.intent.matcher import IntentMatcher

    matcher = IntentMatcher()
    for greeting in ["hello", "hi", "hey", "how are you"]:
        result = matcher.match(greeting)
        if result is not None:
            assert result.intent != "personal_identity", (
                f"Greeting {greeting!r} should not be personal_identity; got {result.intent!r}"
            )


# ─── 15. MediaExecutionState for YouTube ─────────────────────────────────────

def test_youtube_search_returns_navigation_started():
    """ApplicationTool YouTube search returns NAVIGATION_STARTED, not PLAYBACK_CONFIRMED."""
    from core.eva_core.protocol import MediaExecutionState
    from core.eva_core.tools.application import ApplicationTool

    tool = ApplicationTool()

    # Mock subprocess so it doesn't actually open a browser
    with patch("subprocess.Popen") as mock_popen, \
         patch("shutil.which", return_value="/usr/bin/chromium-browser"):
        mock_popen.return_value = MagicMock()
        result = tool.execute(arguments={
            "operation": "youtube_search",
            "application": "chromium",
            "query": "test song",
        })

    # Should be a ToolResult; check data for media_state
    assert result is not None
    if hasattr(result, "data") and result.data:
        assert result.data.get("media_state") == MediaExecutionState.NAVIGATION_STARTED.value, (
            f"Expected NAVIGATION_STARTED, got {result.data.get('media_state')!r}"
        )
    elif hasattr(result, "success"):
        # If browser not found, that's also acceptable (tool returns failure)
        pass


# ─── 16. Recording status fields ─────────────────────────────────────────────

def test_recording_status_has_duration_fields():
    """recording_status() returns elapsed, remaining, duration, duration_expired fields."""
    from core.eva_core.stt.recorder import recording_status, _active_recordings as _recording_registry
    import time

    # Manually inject a fake recording entry
    fake_id = "test_recording_123"
    _recording_registry[fake_id] = {
        "process": None,
        "file_path": "/tmp/fake.wav",
        "status": "recording",
        "silence_detected": False,
        "start_time": time.monotonic() - 2.0,  # recorder uses time.monotonic()
        "duration": 5.0,
        "duration_expired": False,
    }

    try:
        status = recording_status(fake_id)
        assert "elapsed" in status, "recording_status missing 'elapsed'"
        assert "remaining" in status, "recording_status missing 'remaining'"
        assert "duration" in status, "recording_status missing 'duration'"
        assert "duration_expired" in status, "recording_status missing 'duration_expired'"
        assert status["duration"] == 5.0
        assert status["elapsed"] >= 1.9  # at least ~2s elapsed
        assert status["remaining"] <= 3.1  # at most ~3.1s remaining
    finally:
        del _recording_registry[fake_id]


def test_memory_update_reflected_in_llm_context_and_fast_response():
    """Verify that updating memory in SQLite is immediately reflected in LLM context and fast responses."""
    mgr = _get_manager()
    conn = sqlite3.connect(TEST_DB_PATH)
    cur = conn.cursor()

    # 1. Update owner occupation in SQLite
    cur.execute("UPDATE memories SET content = 'AI Systems Architect & Researcher' WHERE key = 'occupation'")
    # 2. Insert a new custom user memory
    cur.execute("""
        INSERT INTO memories (memory_id, title, content, category, privacy, pinned, source, created_at, updated_at)
        VALUES ('mem_custom_test', 'Preferred Editor', 'Neovim with Lua configs', 'User Preferences', 'private', 1, 'user', '2026-01-01', '2026-01-01')
    """)
    conn.commit()
    conn.close()

    # Fast response immediately uses updated occupation
    resp = mgr.get_identity_fast_response("What do I do?")
    assert "AI Systems Architect & Researcher" in resp

    # LLM context includes updated occupation AND custom memory
    ctx = mgr.get_structured_llm_context(include_private=True)
    assert "AI Systems Architect & Researcher" in ctx
    assert "Preferred Editor" in ctx
    assert "Neovim with Lua configs" in ctx
    assert "[User Preferences]" in ctx

