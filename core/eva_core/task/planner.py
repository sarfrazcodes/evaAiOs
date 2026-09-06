import logging
from typing import List, Optional
from core.eva_core.llm.provider import PlanningProvider
from core.eva_core.protocol import TaskStep, TaskPlan, generate_id

MAX_PLAN_STEPS = 10

class Planner:
    def __init__(self, provider: PlanningProvider):
        self.provider = provider

    async def generate_plan(self, task_id: str, request_content: str) -> List[TaskStep]:
        system_prompt = f"""You are the Task Planner for EVA AI OS.
The user has requested a complex task. Your job is to break it down into manageable, logical steps.
Return a JSON object containing a "steps" array.
Each step must have:
- "description": A string describing the step.
- "dependencies": A list of 1-based integers representing the step indices this step depends on. (e.g. [1, 2]). Leave empty [] if no dependencies.

DO NOT create more than {MAX_PLAN_STEPS} steps.
Never include OS execution commands, just describe the logical action.
"""
        
        logging.info(f"Generating plan for task {task_id}")
        raw_result = await self.provider.generate_plan(f"User Request: {request_content}", system_prompt)
        
        try:
            # Validate with Pydantic
            plan = TaskPlan(**raw_result)
        except Exception as e:
            logging.error(f"LLM returned invalid plan structure: {e}")
            raise ValueError(f"Invalid plan format: {e}")
            
        if not plan.steps:
            raise ValueError("Planner returned an empty plan.")
            
        if len(plan.steps) > MAX_PLAN_STEPS:
            logging.warning(f"Plan exceeded max steps limit, truncating to {MAX_PLAN_STEPS}")
            plan.steps = plan.steps[:MAX_PLAN_STEPS]

        # Convert LLM plan indices to real TaskSteps with UUIDs
        task_steps = []
        # Create steps with UUIDs first
        for i, plan_step in enumerate(plan.steps):
            if not plan_step.description.strip():
                raise ValueError("Step description cannot be empty.")
            
            ts = TaskStep(
                task_id=task_id,
                sequence=i + 1,
                description=plan_step.description.strip()
            )
            task_steps.append(ts)
            
        # Wire up dependencies
        for i, plan_step in enumerate(plan.steps):
            deps = []
            if not plan_step.dependencies and i > 0:
                # If LLM didn't specify dependencies, infer linear dependencies
                deps.append(task_steps[i - 1].step_id)
            else:
                for dep_idx in plan_step.dependencies:
                    # Validate dependency bounds
                    if dep_idx < 1 or dep_idx > len(task_steps):
                        logging.warning(f"Invalid dependency index {dep_idx} skipped.")
                        continue
                    if dep_idx == i + 1:
                        raise ValueError("Step cannot depend on itself.")
                    
                    dep_step_id = task_steps[dep_idx - 1].step_id
                    deps.append(dep_step_id)
                    
            task_steps[i].dependencies = deps

        # Simple Cycle Detection (using DFS on DAG)
        self._validate_no_cycles(task_steps)
        
        return task_steps

    def _validate_no_cycles(self, steps: List[TaskStep]):
        visited = set()
        recursion_stack = set()
        
        step_map = {step.step_id: step for step in steps}
        
        def dfs(node_id):
            if node_id in recursion_stack:
                raise ValueError("Circular dependency detected in plan.")
            if node_id in visited:
                return
            
            visited.add(node_id)
            recursion_stack.add(node_id)
            
            node = step_map.get(node_id)
            if node:
                for dep in node.dependencies:
                    dfs(dep)
            
            recursion_stack.remove(node_id)
            
        for step in steps:
            dfs(step.step_id)
