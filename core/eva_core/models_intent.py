from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class IntentModel(BaseModel):
    intent: str
    confidence: float
    reason: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class RouteResult(BaseModel):
    route: str
    intent: str
    confidence: float
