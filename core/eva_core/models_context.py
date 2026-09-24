from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def generate_id() -> str:
    return str(uuid.uuid4())

class ConversationMessage(BaseModel):
    message_id: str = Field(default_factory=generate_id)
    conversation_id: str
    role: str # "user" or "assistant"
    content: str
    created_at: datetime = Field(default_factory=utc_now)

class Conversation(BaseModel):
    conversation_id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    messages: List[ConversationMessage] = Field(default_factory=list)
