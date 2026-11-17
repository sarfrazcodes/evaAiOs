import logging
from typing import List, Dict, Any
from core.eva_core.protocol import TaskStatus
from core.eva_core.task.state import TaskStateManager
from core.eva_core.task.events import TaskEventManager

class RecoveryManager:
    """Safely inspects and recovers interrupted or uncompleted tasks across crashes/restarts."""

    def __init__(self, state_manager: TaskStateManager, event_manager: TaskEventManager):
        self.state_manager = state_manager
        self.event_manager = event_manager

    def recover_interrupted_tasks(self) -> List[Dict[str, Any]]:
        """Scans database for tasks interrupted in RUNNING or inconsistent states and recovers them."""
        recovered = []
        try:
            tasks = self.state_manager.list_tasks(limit=100)
            for task in tasks:
                if task.status in {TaskStatus.RUNNING, "running"}:
                    logging.info(f"Recovering interrupted task: {task.task_id} ({task.intent})")
                    # Check step states
                    all_done = True
                    has_pending = False
                    for step in task.steps:
                        if step.status == "running":
                            # Reset crashed step to pending so it can safely execute
                            self.state_manager.update_step(step.step_id, status="pending")
                            has_pending = True
                            all_done = False
                        elif step.status == "pending":
                            has_pending = True
                            all_done = False
                        elif step.status in {"failed", "blocked"}:
                            all_done = False

                    if all_done and task.steps:
                        self.state_manager.transition_task(task.task_id, TaskStatus.COMPLETED)
                        new_status = TaskStatus.COMPLETED
                    else:
                        # Reset task to READY so ExecutionWorker or user can resume without duplicate work
                        self.state_manager.transition_task(task.task_id, TaskStatus.READY)
                        new_status = TaskStatus.READY

                    self.event_manager.emit(
                        task.task_id,
                        "task_recovered",
                        {"previous_status": task.status, "new_status": new_status, "total_steps": task.total_steps}
                    )
                    recovered.append({"task_id": task.task_id, "status": new_status, "intent": task.intent})

        except Exception as e:
            logging.error(f"Error during task recovery: {e}")

        return recovered
