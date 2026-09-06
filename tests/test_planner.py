import pytest
import sys
import os
from typing import Dict, Any
from core.eva_core.task.planner import Planner, MAX_PLAN_STEPS
from core.eva_core.llm.provider import PlanningProvider

class MockPlanningProvider(PlanningProvider):
    def __init__(self, mock_response: Dict[str, Any]):
        self.mock_response = mock_response

    async def generate_plan(self, prompt: str, system: str = "") -> Dict[str, Any]:
        if "error" in self.mock_response:
            raise RuntimeError(self.mock_response["error"])
        return self.mock_response

@pytest.mark.asyncio
async def test_planner_basic_linear():
    mock_resp = {
        "steps": [
            {"description": "Step 1", "dependencies": []},
            {"description": "Step 2", "dependencies": []}
        ]
    }
    planner = Planner(MockPlanningProvider(mock_resp))
    steps = await planner.generate_plan("task_123", "Do things")
    
    assert len(steps) == 2
    assert steps[0].sequence == 1
    # Check linear dependency inference
    assert len(steps[1].dependencies) == 1
    assert steps[1].dependencies[0] == steps[0].step_id

@pytest.mark.asyncio
async def test_planner_explicit_dependencies():
    mock_resp = {
        "steps": [
            {"description": "A", "dependencies": []},
            {"description": "B", "dependencies": []},
            {"description": "C", "dependencies": [1, 2]}
        ]
    }
    planner = Planner(MockPlanningProvider(mock_resp))
    steps = await planner.generate_plan("task_123", "Complex")
    
    assert len(steps) == 3
    assert len(steps[2].dependencies) == 2
    assert steps[0].step_id in steps[2].dependencies
    assert steps[1].step_id in steps[2].dependencies

@pytest.mark.asyncio
async def test_planner_circular_dependency_rejection():
    mock_resp = {
        "steps": [
            {"description": "A", "dependencies": [2]},
            {"description": "B", "dependencies": [1]}
        ]
    }
    planner = Planner(MockPlanningProvider(mock_resp))
    with pytest.raises(ValueError, match="Circular dependency"):
        await planner.generate_plan("task_123", "Circle")

@pytest.mark.asyncio
async def test_planner_self_dependency_rejection():
    mock_resp = {
        "steps": [
            {"description": "A", "dependencies": [1]}
        ]
    }
    planner = Planner(MockPlanningProvider(mock_resp))
    with pytest.raises(ValueError, match="Step cannot depend on itself"):
        await planner.generate_plan("task_123", "Self")

@pytest.mark.asyncio
async def test_planner_excessive_steps_truncated():
    steps = [{"description": f"Step {i}", "dependencies": []} for i in range(MAX_PLAN_STEPS + 5)]
    mock_resp = {"steps": steps}
    
    planner = Planner(MockPlanningProvider(mock_resp))
    result_steps = await planner.generate_plan("task_123", "Too many")
    
    assert len(result_steps) == MAX_PLAN_STEPS
