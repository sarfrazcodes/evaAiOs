import asyncio
import json
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set

class TaskEventManager:
    """Manages persistent event streams and reconnection ring buffers for agent tasks."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TaskEventManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, history_limit: int = 200):
        if getattr(self, "_initialized", False):
            return
        self.history_limit = history_limit
        self._history: Dict[str, deque] = {}
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = threading.Lock()
        self._initialized = True

    def emit(self, task_id: str, event_type: str, data: Optional[Dict[str, Any]] = None, step_id: Optional[str] = None):
        """Emits an event for a given task and dispatches it to active listeners."""
        payload = {
            "task_id": task_id,
            "event_type": event_type,
            "step_id": step_id,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with self._lock:
            if task_id not in self._history:
                self._history[task_id] = deque(maxlen=self.history_limit)
            self._history[task_id].append(payload)

            subscribers = list(self._subscribers.get(task_id, set()))

        for queue in subscribers:
            try:
                queue.put_nowait(payload)
            except Exception as e:
                logging.debug(f"Failed to queue task event to subscriber: {e}")

    def get_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Returns the replay buffer of events for the specified task."""
        with self._lock:
            if task_id in self._history:
                return list(self._history[task_id])
            return []

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """Registers a new subscriber queue for real-time task event streaming."""
        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            if task_id not in self._subscribers:
                self._subscribers[task_id] = set()
            self._subscribers[task_id].add(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue):
        """Unregisters an active subscriber queue."""
        with self._lock:
            if task_id in self._subscribers:
                self._subscribers[task_id].discard(queue)
                if not self._subscribers[task_id]:
                    del self._subscribers[task_id]

    async def event_generator(self, task_id: str, include_history: bool = True):
        """Yields newline-delimited JSON events for HTTP streaming, starting with past replay history."""
        queue = self.subscribe(task_id)
        try:
            if include_history:
                history = self.get_history(task_id)
                for event in history:
                    yield json.dumps({"type": "history_event", **event}) + "\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield json.dumps({"type": "task_event", **event}) + "\n"
                    if event.get("event_type") in {"task_completed", "task_failed", "task_cancelled"}:
                        break
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat to prevent HTTP client socket drop
                    yield json.dumps({"type": "ping", "task_id": task_id, "timestamp": datetime.now(timezone.utc).isoformat()}) + "\n"
        finally:
            self.unsubscribe(task_id, queue)
