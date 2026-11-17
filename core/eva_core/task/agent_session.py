import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

class AgentSession:
    """Tracks contextual state, active target entities, and multi-turn references for an agent session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.active_directory: Optional[str] = None
        self.active_file: Optional[str] = None
        self.active_app: Optional[str] = None
        self.last_action: Optional[Dict[str, Any]] = None
        self.action_history: List[Dict[str, Any]] = []
        self.task_ids: List[str] = []
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def record_action(self, action_type: str, details: Dict[str, Any]):
        """Records an action and updates active entities."""
        record = {
            "action_type": action_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.action_history.append(record)
        self.last_action = record
        self.updated_at = datetime.now(timezone.utc)

        # Entity tracking
        if "directory" in details or "folder" in details:
            self.active_directory = details.get("directory") or details.get("folder")
        if "path" in details:
            p = details["path"]
            if "." in p.split("/")[-1]:
                self.active_file = p
            else:
                self.active_directory = p
        if "file" in details:
            self.active_file = details["file"]
        if "application" in details or "app" in details:
            self.active_app = details.get("application") or details.get("app")

    def resolve_reference(self, text: str) -> Dict[str, Optional[str]]:
        """Resolves pronouns and implicit references based on session context."""
        lower = text.lower()
        resolved = {
            "directory": None,
            "file": None,
            "application": None,
        }

        # Folder / directory references: "inside it", "in it", "in that folder", "inside the folder"
        if any(w in lower for w in ["inside it", "in it", "in that folder", "inside the folder", "into it"]):
            resolved["directory"] = self.active_directory

        # File references: "in dfs.cpp", "to that file", "to it", "in that file"
        if any(w in lower for w in ["in it", "to it", "the file", "that file", "implement", "add comments"]):
            resolved["file"] = self.active_file

        # App references: "close it", "focus it", "minimize it"
        if any(w in lower for w in ["close it", "focus it", "minimize it", "switch to it"]):
            resolved["application"] = self.active_app

        return resolved

    def attach_task(self, task_id: str):
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)


class SessionManager:
    """Registry of persistent active agent sessions."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance._sessions: Dict[str, AgentSession] = {}
        return cls._instance

    def get_or_create(self, session_id: str) -> AgentSession:
        if not session_id:
            session_id = "default"
        if session_id not in self._sessions:
            self._sessions[session_id] = AgentSession(session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[AgentSession]:
        return self._sessions.get(session_id)
