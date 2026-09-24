from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def generate_id() -> str:
    return str(uuid.uuid4())

class ActionModel(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class ErrorModel(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class RequestModel(BaseModel):
    request_id: str = Field(default_factory=generate_id)
    session_id: Optional[str] = None
    source: str
    input_type: str
    content: str
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)

class ResponseModel(BaseModel):
    request_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorModel] = None
    timestamp: datetime = Field(default_factory=utc_now)

class ToolResult(BaseModel):
    success: bool
    tool_name: str
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)

class TaskStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_CLARIFICATION = "requires_clarification"
    BLOCKED = "blocked"
    ACTION_RESOLUTION_REQUIRED = "action_resolution_required"

class TaskStep(BaseModel):
    step_id: str = Field(default_factory=generate_id)
    task_id: str
    sequence: int
    description: str
    dependencies: List[str] = Field(default_factory=list)
    action: Optional[ActionModel] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[ErrorModel] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

class TaskModel(BaseModel):
    task_id: str = Field(default_factory=generate_id)
    request_id: str
    intent: Optional[str] = None
    status: str = TaskStatus.CREATED
    current_step: int = 0
    total_steps: int = 0
    steps: List[TaskStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    result: Optional[Dict[str, Any]] = None
    error: Optional[ErrorModel] = None

class TaskPlanStep(BaseModel):
    description: str
    dependencies: List[int] = Field(default_factory=list)

class TaskPlan(BaseModel):
    steps: List[TaskPlanStep] = Field(default_factory=list)
