import logging
import threading
from core.eva_core.task.state import TaskStateManager
from core.eva_core.protocol import TaskStatus
from core.eva_core.tools.registry import ToolRegistry
from core.eva_core.permissions.hook import PermissionHook, PermissionDecision

class Executor:
    def __init__(self, state_manager: TaskStateManager, tool_registry: ToolRegistry, permission_hook: PermissionHook):
        self.state_manager = state_manager
        self.tool_registry = tool_registry
        self.permission_hook = permission_hook
        self._execution_lock = threading.Lock()

    def _invalid_dependencies(self, task):
        step_ids = {step.step_id for step in task.steps}
        invalid = []
        for step in task.steps:
            missing = set(step.dependencies) - step_ids
            if step.step_id in step.dependencies or missing:
                invalid.append((step, missing))
        if invalid:
            return invalid

        step_map = {step.step_id: step for step in task.steps}
        visiting = set()
        visited = set()

        def visit(step_id):
            if step_id in visiting:
                return True
            if step_id in visited:
                return False
            visiting.add(step_id)
            if any(visit(dependency) for dependency in step_map[step_id].dependencies):
                return True
            visiting.remove(step_id)
            visited.add(step_id)
            return False

        if any(visit(step.step_id) for step in task.steps):
            return [(task.steps[0], set())]
        return invalid

    def execute_task(self, task_id: str, confirmation_id: str | None = None, control=None) -> None:
        task = self.state_manager.get_task(task_id)
        if not task:
            logging.error(f"Task {task_id} not found.")
            return

        if task.status not in [TaskStatus.PLANNED, TaskStatus.READY]:
            logging.info(f"Task {task_id} is in status {task.status}, skipping execution.")
            return

        invalid_dependencies = self._invalid_dependencies(task)
        if invalid_dependencies:
            for step, missing in invalid_dependencies:
                self.state_manager.update_step(
                    step.step_id,
                    status="failed",
                    error={
                        "code": "InvalidDependency",
                        "message": "Step has a missing or self-referential dependency.",
                        "details": {"missing": sorted(missing)},
                    },
                )
            self.state_manager.transition_task(task_id, TaskStatus.FAILED)
            return

        with self._execution_lock:
            if not self.state_manager.claim_execution(task_id):
                logging.info("Task %s is already claimed or no longer executable.", task_id)
                return

        has_more_steps = True
        action_resolution_needed = False
        confirmation_needed = False

        while has_more_steps:
            if control is not None:
                action = control.wait_if_paused_or_stopped()
                if action == "paused":
                    if self.state_manager.get_task(task_id).status == TaskStatus.RUNNING:
                        self.state_manager.transition_task(task_id, TaskStatus.PAUSED)
                    return
                if action == "stopped":
                    if self.state_manager.get_task(task_id).status == TaskStatus.RUNNING:
                        self.state_manager.transition_task(task_id, TaskStatus.INTERRUPTED)
                    return
            has_more_steps = False
            task = self.state_manager.get_task(task_id)
            
            all_completed = True
            any_failed = False

            for step in task.steps:
                if step.status == "pending":
                    all_completed = False
                    
                    deps_met = True
                    dep_failed = False
                    for dep_seq in step.dependencies:
                        dep_step = next((s for s in task.steps if s.step_id == dep_seq), None)
                        if not dep_step:
                            continue 
                            
                        if dep_step.status == "failed" or dep_step.status == "blocked":
                            dep_failed = True
                            deps_met = False
                            break
                        elif dep_step.status != "completed":
                            deps_met = False
                            break

                    if dep_failed:
                        self.state_manager.update_step(step.step_id, status="blocked", error={"code": "DependencyFailure", "message": "Dependency failed or blocked."})
                        has_more_steps = True
                        continue

                    if not deps_met:
                        continue 
                        
                    if not step.action:
                        self.state_manager.update_step(step.step_id, status="failed", error={"code": "ActionResolutionRequired", "message": "Action resolution required."})
                        action_resolution_needed = True
                        has_more_steps = True
                        continue

                    tool = self.tool_registry.get(step.action.tool)
                    if not tool:
                        self.state_manager.update_step(step.step_id, status="failed", error={"code": "UnknownTool", "message": f"Unknown tool: {step.action.tool}"})
                        has_more_steps = True
                        continue

                    if confirmation_id:
                        confirmation = self.state_manager.get_confirmation(confirmation_id)
                        if not confirmation or confirmation.get("status") != "approved":
                            self.state_manager.update_step(step.step_id, status="blocked", error={"code": "InvalidConfirmation", "message": "Confirmation is not approved or has expired."})
                            confirmation_needed = True
                            has_more_steps = True
                            continue
                        if not self.state_manager.consume_confirmation(confirmation_id, task_id, step.step_id, step.action.tool, step.action.arguments):
                            self.state_manager.update_step(step.step_id, status="blocked", error={"code": "ConfirmationAlreadyUsed", "message": "Confirmation could not be consumed."})
                            confirmation_needed = True
                            has_more_steps = True
                            continue
                        decision = self.permission_hook.check_approved_permission(step.action.tool, step.action.arguments)
                    else:
                        decision = self.permission_hook.check_permission(step.action.tool, step.action.arguments)
                    if decision == PermissionDecision.DENY:
                        self.state_manager.update_step(step.step_id, status="failed", error={"code": "PermissionDenied", "message": "Permission denied."})
                        has_more_steps = True
                        continue
                    elif decision == PermissionDecision.REQUIRE_CONFIRMATION:
                        confirmation = self.state_manager.create_or_get_confirmation(task_id, step.step_id, step.action.tool, step.action.arguments)
                        self.state_manager.update_step(step.step_id, status="blocked", error={"code": "RequiresConfirmation", "message": "Requires confirmation.", "details": {"confirmation_id": confirmation["confirmation_id"], "tool_name": step.action.tool, "arguments": step.action.arguments, "expires_at": confirmation["expires_at"]}})
                        confirmation_needed = True
                        has_more_steps = True
                        continue

                    self.state_manager.update_step(step.step_id, status="running")
                    try:
                        result = tool.execute(step.action.arguments)
                        if result.success:
                            self.state_manager.update_step(step.step_id, status="completed", result=result.model_dump(mode='json'))
                        else:
                            self.state_manager.update_step(step.step_id, status="failed", error={"code": result.error or "ToolError", "message": result.message})
                    except Exception as e:
                        self.state_manager.update_step(step.step_id, status="failed", error={"code": "ExecutionError", "message": "Execution error", "details": {"exception": str(e)}})
                        
                    has_more_steps = True 
                    
                elif step.status in ["failed", "blocked"]:
                    all_completed = False
                    any_failed = True

            if has_more_steps:
                continue

            if action_resolution_needed:
                self.state_manager.transition_task(task_id, TaskStatus.ACTION_RESOLUTION_REQUIRED)
            elif confirmation_needed:
                self.state_manager.transition_task(task_id, TaskStatus.BLOCKED)
            elif all_completed:
                self.state_manager.transition_task(task_id, TaskStatus.COMPLETED)
            elif any_failed:
                self.state_manager.transition_task(task_id, TaskStatus.FAILED)
