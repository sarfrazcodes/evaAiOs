import logging
import threading
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
import heapq

@dataclass(order=True)
class PrioritizedTask:
    priority: int
    task_id: str = field(compare=False)
    confirmation_id: Optional[str] = field(default=None, compare=False)

class TaskQueue:
    """Thread-safe priority queue for persistent task scheduling."""

    def __init__(self):
        self._heap: List[PrioritizedTask] = []
        self._task_set: Dict[str, PrioritizedTask] = {}
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def enqueue(self, task_id: str, priority: int = 10, confirmation_id: Optional[str] = None) -> bool:
        """Enqueues a task for execution. Returns False if already in the queue."""
        with self._lock:
            if task_id in self._task_set:
                logging.info(f"Task {task_id} is already in the execution queue.")
                return False
            item = PrioritizedTask(priority=priority, task_id=task_id, confirmation_id=confirmation_id)
            heapq.heappush(self._heap, item)
            self._task_set[task_id] = item
            self._not_empty.notify()
            logging.info(f"Enqueued task {task_id} with priority {priority}.")
            return True

    def dequeue(self, timeout: Optional[float] = None) -> Optional[Tuple[str, Optional[str]]]:
        """Dequeues the highest priority task (lowest priority number). Blocks until available or timeout."""
        with self._not_empty:
            while not self._heap:
                not_empty_success = self._not_empty.wait(timeout=timeout)
                if not not_empty_success or not self._heap:
                    return None

            item = heapq.heappop(self._heap)
            if item.task_id in self._task_set:
                del self._task_set[item.task_id]
            return item.task_id, item.confirmation_id

    def cancel(self, task_id: str) -> bool:
        """Removes a task from the queue if it has not yet started running."""
        with self._lock:
            if task_id in self._task_set:
                del self._task_set[task_id]
                self._heap = [t for t in self._heap if t.task_id != task_id]
                heapq.heapify(self._heap)
                return True
            return False

    def contains(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._task_set

    def size(self) -> int:
        with self._lock:
            return len(self._task_set)

    def list_queued(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"task_id": t.task_id, "priority": t.priority} for t in self._heap]
