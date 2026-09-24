import pytest
import os
import sys
import sqlite3
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Mock os.environ before imports if needed, but db path is relative
from core.eva_core.context.manager import ConversationContextManager
from core.eva_core.models_context import ConversationMessage
import core.eva_core.database as db_module

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_context.db')

@pytest.fixture(autouse=True)
def clean_db():
    db_module.DB_PATH = TEST_DB_PATH
    db_module.init_db()
    
    conn = sqlite3.connect(db_module.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations")
    cursor.execute("DELETE FROM conversation_messages")
    conn.commit()
    conn.close()
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_conversation_creation():
    manager = ConversationContextManager()
    conv_id = manager.create_conversation()
    assert conv_id is not None
    assert isinstance(conv_id, str)
    
    conv = manager.get_conversation(conv_id)
    assert conv is not None
    assert conv.conversation_id == conv_id

def test_add_messages_and_retrieval():
    manager = ConversationContextManager()
    conv_id = manager.create_conversation()
    
    msg1 = manager.add_user_message(conv_id, "Hello")
    msg2 = manager.add_assistant_message(conv_id, "Hi there")
    
    assert msg1.role == "user"
    assert msg2.role == "assistant"
    
    recent = manager.get_recent_messages(conv_id)
    assert len(recent) == 2
    assert recent[0].content == "Hello"
    assert recent[1].content == "Hi there"
    
def test_message_ordering_and_limit():
    # Patch the MAX_MESSAGES for this test
    with patch('core.eva_core.context.manager.MAX_MESSAGES', 3):
        manager = ConversationContextManager()
        conv_id = manager.create_conversation()
        
        manager.add_user_message(conv_id, "Message 1")
        manager.add_assistant_message(conv_id, "Message 2")
        manager.add_user_message(conv_id, "Message 3")
        manager.add_assistant_message(conv_id, "Message 4")
        
        recent = manager.get_recent_messages(conv_id, limit=3)
        assert len(recent) == 3
        # Should be the last 3 messages in chronological order
        assert recent[0].content == "Message 2"
        assert recent[1].content == "Message 3"
        assert recent[2].content == "Message 4"

def test_conversation_isolation():
    manager = ConversationContextManager()
    conv_id_1 = manager.create_conversation()
    conv_id_2 = manager.create_conversation()
    
    manager.add_user_message(conv_id_1, "Conv 1 User")
    manager.add_assistant_message(conv_id_2, "Conv 2 Assistant")
    
    recent1 = manager.get_recent_messages(conv_id_1)
    recent2 = manager.get_recent_messages(conv_id_2)
    
    assert len(recent1) == 1
    assert recent1[0].content == "Conv 1 User"
    
    assert len(recent2) == 1
    assert recent2[0].content == "Conv 2 Assistant"

def test_clear_conversation():
    manager = ConversationContextManager()
    conv_id = manager.create_conversation()
    manager.add_user_message(conv_id, "Hello")
    manager.add_assistant_message(conv_id, "Hi")
    
    manager.clear_conversation(conv_id)
    
    recent = manager.get_recent_messages(conv_id)
    assert len(recent) == 0

def test_format_llm_context():
    manager = ConversationContextManager()
    conv_id = manager.create_conversation()
    
    manager.add_user_message(conv_id, "What is an AI agent?")
    manager.add_assistant_message(conv_id, "An AI agent is a system...")
    
    context_str = manager.format_llm_context(conv_id, "What can it do?")
    
    assert "User:\nWhat is an AI agent?" in context_str
    assert "Assistant:\nAn AI agent is a system..." in context_str
    assert "CURRENT USER REQUEST:\n\"What can it do?\"" in context_str

# Test streaming endpoint integration
from core.eva_core.main import app

def test_streaming_endpoint_context():
    client = TestClient(app)
    
    # Send first message
    response = client.post("/api/v1/core/chat/stream", json={
        "source": "test",
        "input_type": "text",
        "content": "What is an AI agent?"
    })
    
    assert response.status_code == 200
    
    # We need to parse NDJSON to find the session_id
    lines = response.text.strip().split('\n')
    session_id = None
    for line in lines:
        data = json.loads(line)
        if data.get("type") == "metadata" and "session_id" in data.get("data", {}):
            session_id = data["data"]["session_id"]
            
    assert session_id is not None
    
    # Verify it was saved to the DB
    manager = ConversationContextManager()
    recent = manager.get_recent_messages(session_id)
    assert len(recent) > 0
    assert any(msg.role == "user" and msg.content == "What is an AI agent?" for msg in recent)
    
    # The assistant response should also be saved
    assistant_msgs = [msg for msg in recent if msg.role == "assistant"]
    assert len(assistant_msgs) > 0
