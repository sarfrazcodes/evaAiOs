import threading
from concurrent.futures import ThreadPoolExecutor

from core.eva_core.protocol import TaskStatus


class TaskControl:
    def __init__(self):
        self.pause_requested = threading.Event()
        self.stop_requested = threading.Event()
        self.resume_event = threading.Event()
        self.resume_event.set()

    def pause(self):
        self.pause_requested.set()
        self.resume_event.clear()

    def resume(self):
        self.pause_requested.clear()
        self.resume_event.set()

    def stop(self):
        self.stop_requested.set()
        self.resume_event.set()

    def wait_if_paused_or_stopped(self):
        if self.stop_requested.is_set():
            return "stopped"
        if self.pause_requested.is_set():
            self.resume_event.wait()
            if self.stop_requested.is_set():
                return "stopped"
        return None


class TaskRunner:
    """Small in-process task runner; SQLite remains the source of task state."""

    def __init__(self, executor, state_manager, max_workers=4):
        self.executor = executor
        self.state_manager = state_manager
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="eva-task")
        self.controls = {}
        self.submitted = set()
        self.lock = threading.Lock()

    def submit(self, task_id, confirmation_id=None, wait_seconds=0):
        with self.lock:
            control = self.controls.setdefault(task_id, TaskControl())
            task = self.state_manager.get_task(task_id)
            if not task or task.status not in {TaskStatus.PLANNED, TaskStatus.READY}:
                return False
            if task_id in self.submitted:
                return False
            self.submitted.add(task_id)
            future = self.pool.submit(self._run, task_id, confirmation_id, control)
            if wait_seconds > 0:
                try:
                    future.result(timeout=wait_seconds)
                except TimeoutError:
                    pass
            return True

    def _run(self, task_id, confirmation_id, control):
        try:
            self.executor.execute_task(task_id, confirmation_id=confirmation_id, control=control)
        except Exception:
            task = self.state_manager.get_task(task_id)
            if task and task.status == TaskStatus.RUNNING:
                self.state_manager.transition_task(task_id, TaskStatus.FAILED)
        finally:
            with self.lock:
                self.submitted.discard(task_id)

    def pause(self, task_id):
        with self.lock:
            control = self.controls.get(task_id)
            task = self.state_manager.get_task(task_id)
            if not control or not task or task.status != TaskStatus.RUNNING:
                return False
            control.pause()
            return True

    def resume(self, task_id):
        with self.lock:
            control = self.controls.get(task_id)
            task = self.state_manager.get_task(task_id)
            if not control or not task or task.status != TaskStatus.PAUSED or task_id in self.submitted:
                return False
            control.resume()
            self.state_manager.transition_task(task_id, TaskStatus.READY)
            self.submitted.add(task_id)
            self.pool.submit(self._run, task_id, None, control)
            return True

    def stop(self, task_id):
        with self.lock:
            control = self.controls.get(task_id)
            task = self.state_manager.get_task(task_id)
            if not control or not task or task.status not in {TaskStatus.RUNNING, TaskStatus.PAUSED}:
                return False
            control.stop()
            if task.status == TaskStatus.PAUSED:
                self.state_manager.transition_task(task_id, TaskStatus.INTERRUPTED)
            return True