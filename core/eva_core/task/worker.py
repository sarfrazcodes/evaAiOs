import logging
import threading
import time
from typing import Optional, Dict
from core.eva_core.protocol import TaskStatus
from core.eva_core.task.state import TaskStateManager
from core.eva_core.executor.executor import Executor
from core.eva_core.task.queue import TaskQueue
from core.eva_core.task.events import TaskEventManager
from core.eva_core.task.runner import TaskControl

class ExecutionWorker:
    """Background daemon worker executing agent tasks persistently and independently of HTTP clients."""

    def __init__(
        self,
        queue: TaskQueue,
        state_manager: TaskStateManager,
        executor: Executor,
        event_manager: TaskEventManager,
    ):
        self.queue = queue
        self.state_manager = state_manager
        self.executor = executor
        self.event_manager = event_manager

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._controls: Dict[str, TaskControl] = {}
        self._active_task_id: Optional[str] = None
        self._lock = threading.Lock()

    def start(self):
        """Starts the background worker thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, name="eva-agent-worker", daemon=True)
            self._thread.start()
            logging.info("ExecutionWorker background thread started.")

    def stop(self):
        """Stops the worker thread."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            logging.info("ExecutionWorker background thread stopped.")

    def get_control(self, task_id: str) -> TaskControl:
        with self._lock:
            if task_id not in self._controls:
                self._controls[task_id] = TaskControl()
            return self._controls[task_id]

    def pause_task(self, task_id: str) -> bool:
        control = self.get_control(task_id)
        task = self.state_manager.get_task(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        control.pause()
        self.event_manager.emit(task_id, "task_paused")
        return True

    def resume_task(self, task_id: str) -> bool:
        control = self.get_control(task_id)
        task = self.state_manager.get_task(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        control.resume()
        self.state_manager.transition_task(task_id, TaskStatus.READY)
        self.queue.enqueue(task_id, priority=5)
        self.event_manager.emit(task_id, "task_resumed")
        return True

    def stop_task(self, task_id: str) -> bool:
        control = self.get_control(task_id)
        control.stop()
        task = self.state_manager.get_task(task_id)
        if task:
            self.state_manager.transition_task(task_id, TaskStatus.CANCELLED)
            self.event_manager.emit(task_id, "task_cancelled")
            return True
        return False

    def _run_loop(self):
        logging.info("ExecutionWorker entering polling loop...")
        while self._running:
            try:
                item = self.queue.dequeue(timeout=0.5)
                if not item:
                    continue

                task_id, confirmation_id = item
                with self._lock:
                    self._active_task_id = task_id

                control = self.get_control(task_id)
                self._execute_single_task(task_id, confirmation_id, control)

            except Exception as e:
                logging.error(f"ExecutionWorker encountered error: {e}", exc_info=True)
            finally:
                with self._lock:
                    self._active_task_id = None

    def _execute_single_task(self, task_id: str, confirmation_id: Optional[str], control: TaskControl):
        task = self.state_manager.get_task(task_id)
        if not task:
            logging.warning(f"Task {task_id} not found for execution.")
            return

        if task.status not in {TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.PENDING}:
            logging.info(f"Task {task_id} is in status {task.status}, skipping execution.")
            return

        logging.info(f"ExecutionWorker executing task {task_id} ({task.intent})...")
        self.event_manager.emit(task_id, "task_started", {"intent": task.intent, "total_steps": task.total_steps})

        try:
            self.executor.execute_task(task_id, confirmation_id=confirmation_id, control=control)
        except Exception as exc:
            logging.error(f"Error executing task {task_id}: {exc}", exc_info=True)
            self.state_manager.transition_task(task_id, TaskStatus.FAILED)
            self.event_manager.emit(task_id, "task_failed", {"error": str(exc)})
            return

        # Verification step
        final_task = self.state_manager.get_task(task_id)
        if final_task:
            if final_task.status == TaskStatus.COMPLETED:
                logging.info(f"Task {task_id} completed successfully.")
                self.event_manager.emit(task_id, "task_completed", {"result": final_task.result})
            elif final_task.status in {TaskStatus.BLOCKED, TaskStatus.WAITING_FOR_CONFIRMATION}:
                logging.info(f"Task {task_id} is awaiting user confirmation.")
                self.event_manager.emit(task_id, "task_waiting_for_confirmation")
            elif final_task.status == TaskStatus.FAILED:
                logging.warning(f"Task {task_id} failed.")
                self.event_manager.emit(task_id, "task_failed", {"error": final_task.error.model_dump() if final_task.error else None})
            elif final_task.status == TaskStatus.PAUSED:
                logging.info(f"Task {task_id} is paused.")
                self.event_manager.emit(task_id, "task_paused")
