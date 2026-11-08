import os

from core.eva_core.intent.matcher import IntentMatcher
from core.eva_core.main import _deterministic_control_plan


def test_lifecycle_and_search_intents():
    matcher = IntentMatcher()
    assert matcher.match("Open Chrome").parameters["operation"] == "open"
    assert matcher.match("Close Firefox").parameters["operation"] == "close"
    assert matcher.match("Focus VS Code").parameters["operation"] == "focus"
    assert matcher.match("Is Chrome running?").parameters["operation"] == "check_running"
    search = matcher.match("Search for Python tutorials in Firefox")
    assert search.intent == "browser_operation"
    assert search.parameters == {"query": "python tutorials", "application": "firefox"}
    assert matcher.match("Search Google for machine learning").parameters["query"] == "machine learning"
    follow_up = matcher.match("Now in a new tab search leetcode")
    assert follow_up.intent == "browser_operation"
    assert follow_up.parameters == {"query": "leetcode", "new_tab": True}
    editor = matcher.match("Open Notepad or whatever text editor is available")
    assert editor.parameters == {"application": "text editor", "operation": "open"}
    assert matcher.match("open notepad").parameters["application"] == "text editor"
    writing = matcher.match("Write a short paragraph about Artificial Intelligence")
    assert writing.intent == "editor_operation"


def test_deterministic_multi_step_open_and_search_plan():
    steps = _deterministic_control_plan(
        "task-1", "Open Firefox and search for Python tutorials"
    )
    assert [step.action.arguments["operation"] for step in steps] == ["open", "search"]
    assert steps[1].dependencies == [steps[0].step_id]
    assert steps[1].action.arguments["application"] == "firefox"
    assert steps[1].action.arguments["query"] == "python tutorials"


def test_deterministic_multi_application_plan():
    steps = _deterministic_control_plan("task-2", "Open Chrome and VS Code")
    assert [step.action.arguments["application"] for step in steps] == ["chrome", "vscode"]
    assert steps[1].dependencies == [steps[0].step_id]
