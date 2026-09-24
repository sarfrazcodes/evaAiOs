import sqlite3
import logging
from typing import List, Optional
from datetime import datetime, timezone
import os
from core.eva_core.models_context import Conversation, ConversationMessage, generate_id, utc_now
import core.eva_core.database as db_module

MAX_MESSAGES = int(os.environ.get("EVA_CONTEXT_MAX_MESSAGES", 12))

class ConversationContextManager:
    def __init__(self):
        pass

    def _get_connection(self):
        return sqlite3.connect(db_module.DB_PATH)

    def create_conversation(self) -> str:
        conversation_id = generate_id()
        now = utc_now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversations (conversation_id, created_at, updated_at) VALUES (?, ?, ?)",
                    (conversation_id, now, now)
                )
                conn.commit()
            return conversation_id
        except Exception as e:
            logging.error(f"Error creating conversation: {e}")
            raise e

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT created_at, updated_at FROM conversations WHERE conversation_id = ?", (conversation_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                
                conv = Conversation(
                    conversation_id=conversation_id,
                    created_at=datetime.fromisoformat(row[0]),
                    updated_at=datetime.fromisoformat(row[1])
                )
                
                cursor.execute(
                    "SELECT message_id, role, content, created_at FROM conversation_messages WHERE conversation_id = ? ORDER BY created_at ASC",
                    (conversation_id,)
                )
                rows = cursor.fetchall()
                for r in rows:
                    msg = ConversationMessage(
                        message_id=r[0],
                        conversation_id=conversation_id,
                        role=r[1],
                        content=r[2],
                        created_at=datetime.fromisoformat(r[3])
                    )
                    conv.messages.append(msg)
                    
                return conv
        except Exception as e:
            logging.error(f"Error getting conversation {conversation_id}: {e}")
            return None

    def add_user_message(self, conversation_id: str, content: str) -> ConversationMessage:
        return self._add_message(conversation_id, "user", content)

    def add_assistant_message(self, conversation_id: str, content: str) -> ConversationMessage:
        return self._add_message(conversation_id, "assistant", content)

    def _add_message(self, conversation_id: str, role: str, content: str) -> ConversationMessage:
        msg = ConversationMessage(conversation_id=conversation_id, role=role, content=content)
        now = msg.created_at.isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM conversations WHERE conversation_id = ?", (conversation_id,))
                if not cursor.fetchone():
                    # Create conversation if it doesn't exist
                    cursor.execute(
                        "INSERT INTO conversations (conversation_id, created_at, updated_at) VALUES (?, ?, ?)",
                        (conversation_id, now, now)
                    )
                
                cursor.execute(
                    "INSERT INTO conversation_messages (message_id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                    (msg.message_id, msg.conversation_id, msg.role, msg.content, now)
                )
                cursor.execute(
                    "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                    (now, conversation_id)
                )
                conn.commit()
            return msg
        except Exception as e:
            logging.error(f"Error adding message to {conversation_id}: {e}")
            raise e

    def get_recent_messages(self, conversation_id: str, limit: int = MAX_MESSAGES) -> List[ConversationMessage]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT message_id, role, content, created_at FROM conversation_messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
                    (conversation_id, limit)
                )
                rows = cursor.fetchall()
                messages = []
                for r in rows:
                    msg = ConversationMessage(
                        message_id=r[0],
                        conversation_id=conversation_id,
                        role=r[1],
                        content=r[2],
                        created_at=datetime.fromisoformat(r[3])
                    )
                    messages.append(msg)
                
                # Reverse to chronological order
                messages.reverse()
                return messages
        except Exception as e:
            logging.error(f"Error retrieving recent messages for {conversation_id}: {e}")
            return []

    def clear_conversation(self, conversation_id: str):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", (conversation_id,))
                cursor.execute("UPDATE conversations SET updated_at = ? WHERE conversation_id = ?", (utc_now().isoformat(), conversation_id))
                conn.commit()
        except Exception as e:
            logging.error(f"Error clearing conversation {conversation_id}: {e}")

    def format_llm_context(self, conversation_id: str, current_request: str) -> str:
        """Formats the recent context to be appended/prepended before the prompt."""
        recent = self.get_recent_messages(conversation_id)
        if not recent:
            return f"CURRENT USER REQUEST:\n\"{current_request}\""
            
        context_str = "CONVERSATION HISTORY:\n\n"
        for msg in recent:
            if msg.role == "user":
                context_str += f"User:\n{msg.content}\n\n"
            else:
                context_str += f"Assistant:\n{msg.content}\n\n"
                
        context_str += f"CURRENT USER REQUEST:\n\"{current_request}\""
        return context_str
