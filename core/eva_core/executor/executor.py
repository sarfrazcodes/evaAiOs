import logging
from core.eva_core.task.state import TaskStateManager
from core.eva_core.protocol import TaskStatus
from core.eva_core.tools.registry import ToolRegistry
from core.eva_core.permissions.hook import PermissionHook, PermissionDecision

class Executor:
    def __init__(self, state_manager: TaskStateManager, tool_registry: ToolRegistry, permission_hook: PermissionHook):
        self.state_manager = state_manager
        self.tool_registry = tool_registry
        self.permission_hook = permission_hook

    def execute_task(self, task_id: str) -> None:
        task = self.state_manager.get_task(task_id)
        if not task:
            logging.error(f"Task {task_id} not found.")
            return

        if task.status not in [TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.RUNNING]:
            logging.info(f"Task {task_id} is in status {task.status}, skipping execution.")
            return

        if task.status == TaskStatus.PLANNED:
            self.state_manager.transition_task(task_id, TaskStatus.READY)
            
        self.state_manager.transition_task(task_id, TaskStatus.RUNNING)

        has_more_steps = True
        action_resolution_needed = False

        while has_more_steps:
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

                    decision = self.permission_hook.check_permission(step.action.tool, step.action.arguments)
                    if decision == PermissionDecision.DENY:
                        self.state_manager.update_step(step.step_id, status="failed", error={"code": "PermissionDenied", "message": "Permission denied."})
                        has_more_steps = True
                        continue
                    elif decision == PermissionDecision.REQUIRE_CONFIRMATION:
                        self.state_manager.update_step(step.step_id, status="blocked", error={"code": "RequiresConfirmation", "message": "Requires confirmation."})
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
            elif all_completed:
                self.state_manager.transition_task(task_id, TaskStatus.COMPLETED)
            elif any_failed:
                self.state_manager.transition_task(task_id, TaskStatus.FAILED)
