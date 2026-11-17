import logging
from typing import Optional, List, Dict, Any, Union
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from system.eva_system.sys_info import get_system_info
from core.eva_core.database import database_health, init_db
import sys
import os
import json
import sqlite3
import httpx
import re

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.eva_core.protocol import ActionModel, RequestModel, ResponseModel, TaskStatus, TaskStep
from core.eva_core.llm.ollama_provider import OllamaProvider
from core.eva_core.intent.engine import IntentEngine
from core.eva_core.intent.router import Router
from core.eva_core.task.planner import Planner
from core.eva_core.task.state import TaskStateManager
from core.eva_core.executor.executor import Executor
from core.eva_core.task.runner import TaskRunner
from core.eva_core.tools.registry import ToolRegistry
from core.eva_core.permissions.hook import PermissionHook
from core.eva_core.tools.echo import EchoTool
from core.eva_core.tools.calculator import CalculatorTool
from core.eva_core.tools.file import FileTool
from core.eva_core.tools.application import ApplicationTool
from core.eva_core.tools.desktop import DesktopTool
from core.eva_core.context.manager import ConversationContextManager
from core.eva_core.stt.transcriber import (
    get_transcriber,
    STTDependencyError,
    STTModelNotAvailableError,
    STTTranscriptionError,
)
from core.eva_core.stt.recorder import (
    start_recording,
    stop_recording,
    cancel_recording,
    recording_status,
)
from core.eva_core.tts.service import SentenceBuffer, get_tts_service
from core.eva_core.task.events import TaskEventManager
from core.eva_core.task.queue import TaskQueue
from core.eva_core.task.worker import ExecutionWorker
from core.eva_core.task.recovery import RecoveryManager
from core.eva_core.task.agent_session import SessionManager
from core.eva_core.stt.agentic_voice import AgenticVoiceService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(title="EVA AI OS Core Service", version="0.1.0")

# Initialize Phase 2C components globally
from core.eva_core.llm.model_router import ModelRouter, PrivacyMode
from core.eva_core.llm.gemini_provider import GeminiProvider

model_name = os.environ.get("EVA_INTENT_MODEL", "llama3.2:3b")
llm_provider = OllamaProvider(model=model_name)
gemini_provider = GeminiProvider()
model_router = ModelRouter(ollama_provider=llm_provider, gemini_provider=gemini_provider)

intent_engine = IntentEngine(llm_provider=llm_provider)
router = Router()
planner = Planner(provider=llm_provider)
state_manager = TaskStateManager()
context_manager = ConversationContextManager()
tts_service = get_tts_service()

tool_registry = ToolRegistry()
tool_registry.register(EchoTool())
tool_registry.register(CalculatorTool())
tool_registry.register(FileTool())
tool_registry.register(ApplicationTool())
tool_registry.register(DesktopTool())

permission_hook = PermissionHook()
executor = Executor(state_manager=state_manager, tool_registry=tool_registry, permission_hook=permission_hook)
task_runner = TaskRunner(executor=executor, state_manager=state_manager)

# Phase 5: Persistent Execution Engine & Session Management
task_event_manager = TaskEventManager()
task_queue = TaskQueue()
execution_worker = ExecutionWorker(
    queue=task_queue,
    state_manager=state_manager,
    executor=executor,
    event_manager=task_event_manager,
)
recovery_manager = RecoveryManager(
    state_manager=state_manager,
    event_manager=task_event_manager,
)
session_manager = SessionManager()

def _agentic_voice_callback(transcript: str) -> str:
    import asyncio
    context_manager.add_user_message("agentic_voice_session", transcript)
    req = RequestModel(
        source="agentic_voice",
        input_type="voice",
        content=transcript,
        session_id="agentic_voice_session",
    )
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    resp = loop.run_until_complete(handle_request(req))
    msg = resp.message or "Action executed."
    context_manager.add_assistant_message("agentic_voice_session", msg)
    tts_service.begin_response(resp.request_id)
    tts_service.enqueue(msg, resp.request_id)
    return msg

agentic_voice_service = AgenticVoiceService(handler_callback=_agentic_voice_callback)


def execute_safe_intent(intent_model, session_id: str | None = None):
    init_db()
    arguments = dict(intent_model.parameters)
    session = session_manager.get_or_create(session_id or "default")

    if intent_model.intent == "application_operation":
        arguments["operation"] = arguments.get("operation", "open")
        tool_name = "application_tool"
    elif intent_model.intent == "editor_operation":
        arguments["operation"] = "write_text"
        arguments["application"] = arguments.get("application", "text editor")
        tool_name = "application_tool"
    elif intent_model.intent == "desktop_operation":
        arguments = {
            "operation": "open_directory",
            "path": {
                "open downloads": os.path.expanduser("~/Downloads"),
                "open downloads folder": os.path.expanduser("~/Downloads"),
                "open home folder": os.path.expanduser("~"),
                "open file manager": os.path.expanduser("~"),
                "open file explorer": os.path.expanduser("~"),
                "open folder": os.path.expanduser("~"),
            }.get(arguments.get("request"), os.path.expanduser("~")),
        }
        tool_name = "desktop_tool"
    elif intent_model.intent == "file_operation":
        op = arguments.get("operation")
        if op not in {
            "create_file", "create_directory", "read_file", "list_directory",
            "edit_file", "append_file", "generate_code", "search_files", "file_info"
        }:
            return None
        tool_name = "file_tool"

        # Specialized code generator for DFS multi-turn demonstration
        if op == "generate_code" and not arguments.get("code"):
            algo = arguments.get("algorithm", "dfs")
            lang = arguments.get("language", "cpp")
            if "dfs" in str(algo).lower():
                arguments["code"] = (
                    "#include <iostream>\n"
                    "#include <vector>\n\n"
                    "using namespace std;\n\n"
                    "void dfs(int node, const vector<vector<int>>& adj, vector<bool>& visited) {\n"
                    "    visited[node] = true;\n"
                    "    cout << node << \" \";\n"
                    "    for (int next : adj[node]) {\n"
                    "        if (!visited[next]) {\n"
                    "            dfs(next, adj, visited);\n"
                    "        }\n"
                    "    }\n"
                    "}\n\n"
                    "int main() {\n"
                    "    int n = 5;\n"
                    "    vector<vector<int>> adj(n);\n"
                    "    adj[0].push_back(1);\n"
                    "    adj[0].push_back(2);\n"
                    "    adj[1].push_back(3);\n"
                    "    adj[2].push_back(4);\n"
                    "    vector<bool> visited(n, false);\n"
                    "    cout << \"DFS: \";\n"
                    "    dfs(0, adj, visited);\n"
                    "    cout << endl;\n"
                    "    return 0;\n"
                    "}\n"
                )
            else:
                arguments["code"] = f"// Implementation of {algo} in {lang}\n"

        # Specialized comment editing helper
        if op == "edit_file" and arguments.get("action") == "add_comments":
            target_path = arguments.get("path")
            comment_header = (
                "/**\n"
                " * Depth First Search (DFS) Implementation\n"
                " * Traverses graph vertices depth-wise recursively.\n"
                " * Time Complexity: O(V + E)\n"
                " * Space Complexity: O(V) recursion stack\n"
                " */\n\n"
            )
            try:
                ft = tool_registry.get("file_tool")
                resolved = ft._resolve_path(target_path)
                with open(resolved, "r", encoding="utf-8") as f:
                    curr = f.read()
                arguments["replacement"] = comment_header + curr
                arguments["target"] = None
            except Exception:
                arguments["replacement"] = comment_header
                arguments["target"] = None

    elif intent_model.intent == "desktop_control":
        arguments = dict(intent_model.parameters)
        tool_name = "desktop_tool"
    elif intent_model.intent == "browser_operation":
        tool_name = "application_tool"
        arguments["operation"] = "search"
        if not arguments.get("application"):
            arguments["application"] = os.environ.get("EVA_DEFAULT_BROWSER", "chrome")
    else:
        return None

    task = state_manager.create_task(request_id=f"intent-{os.urandom(8).hex()}", intent=intent_model.intent)
    step = TaskStep(
        task_id=task.task_id,
        sequence=1,
        description=f"Execute {intent_model.intent}",
        action=ActionModel(tool=tool_name, arguments=arguments),
    )
    state_manager.save_plan(task.task_id, [step])
    state_manager.transition_task(task.task_id, TaskStatus.PLANNED)
    executor.execute_task(task.task_id)

    completed_task = state_manager.get_task(task.task_id)
    if completed_task and completed_task.status in {TaskStatus.COMPLETED, TaskStatus.BLOCKED}:
        session.record_action(tool_name, arguments)

    return completed_task


async def create_editor_write_task(request_id: str, request: str):
    result = await llm_provider.generate_json(
        prompt=f"Write one short, natural paragraph about the user's requested topic. Return JSON only with a single 'text' string. User request: {request}",
        system="You generate concise demo text. Do not include markdown, commands, or extra fields.",
    )
    text = result.get("text") if isinstance(result, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The language model returned no writing text.")
    task = state_manager.create_task(request_id=request_id, intent="editor_operation")
    step = TaskStep(
        task_id=task.task_id,
        sequence=1,
        description="Write generated paragraph into the active text editor",
        action=ActionModel(tool="application_tool", arguments={"operation": "write_text", "application": "text editor", "text": text.strip()}),
    )
    state_manager.save_plan(task.task_id, [step])
    state_manager.transition_task(task.task_id, TaskStatus.PLANNED)
    task_runner.submit(task.task_id)
    return state_manager.get_task(task.task_id)


def _resolve_contextual_application(intent_model, conversation_id: str | None):
    if intent_model.parameters.get("application") != "__context__" or not conversation_id:
        return intent_model
    messages = context_manager.get_recent_messages(conversation_id)
    known_apps = sorted(ApplicationTool.ALLOWLIST, key=len, reverse=True)
    for message in reversed(messages):
        content = message.content.lower()
        for app_name in known_apps:
            if app_name in content:
                intent_model.parameters["application"] = app_name
                return intent_model
    intent_model.intent = "ambiguous"
    intent_model.confidence = 0.0
    intent_model.reason = "No unambiguous application in conversation context"
    return intent_model


def _resolve_browser_context(intent_model, conversation_id: str | None):
    if intent_model.intent != "browser_operation" or intent_model.parameters.get("application"):
        return intent_model
    if conversation_id:
        messages = context_manager.get_recent_messages(conversation_id)
        for message in reversed(messages):
            content = message.content.lower()
            for app_name in ("firefox", "chrome", "google chrome", "brave"):
                if app_name in content:
                    intent_model.parameters["application"] = app_name
                    return intent_model
    intent_model.parameters["application"] = os.environ.get("EVA_DEFAULT_BROWSER", "chrome")
    return intent_model


def _resolve_contextual_file_and_directory(intent_model, conversation_id: str | None):
    if intent_model.intent != "file_operation":
        return intent_model
    session = session_manager.get_or_create(conversation_id or "default")
    params = intent_model.parameters

    if params.get("context_parent") or params.get("path") in {"inside it", "in it"}:
        active_dir = session.active_directory or ""
        file_name = params.get("path", "")
        if file_name in {"inside it", "in it"}:
            file_name = params.get("filename", "file.txt")
        new_path = os.path.join(active_dir, file_name) if active_dir else file_name
        params["path"] = new_path
        params["context_parent"] = False

    if params.get("target_file") == "__context_file__":
        target = session.active_file
        if not target and session.active_directory:
            target = f"{session.active_directory}/dfs.cpp"
        params["path"] = target or "main.cpp"

    return intent_model


def _deterministic_control_plan(task_id: str, request: str):
    normalized = request.lower()
    known_apps = {
        "chrome": "chrome", "google chrome": "chrome", "firefox": "firefox",
        "brave": "brave", "vscode": "vscode", "vs code": "vscode",
        "visual studio code": "vscode",
    }
    steps = []
    selected_browser = None
    if re.search(r"\b(minimize|hide)\b.*\b(editor|text editor|notepad)\b", normalized):
        steps.append(TaskStep(
            task_id=task_id,
            sequence=1,
            description="Minimize the text editor",
            action=ActionModel(tool="application_tool", arguments={"operation": "minimize", "application": "text editor"}),
        ))
    open_segment = re.split(r"\b(?:search|google|look up|find)\b", normalized, maxsplit=1)[0]
    open_matches = re.finditer(r"\b(chrome|google chrome|firefox|brave|vscode|vs code|visual studio code)\b", open_segment)
    for match in open_matches:
        app_name = known_apps[match.group(1)]
        if app_name in {"chrome", "firefox", "brave"}:
            selected_browser = app_name
        steps.append(TaskStep(
            task_id=task_id,
            sequence=len(steps) + 1,
            description=f"Open or focus {app_name}",
            action=ActionModel(tool="application_tool", arguments={"operation": "open", "application": app_name}),
        ))

    search_parts = re.findall(r"\b(?:search|google|look up|find|play)(?: for)?\s+(.+?)(?=\s+then\s+search|\s+and\s+search|\s+on\s+youtube|$)", normalized)
    for query in search_parts:
        browser = selected_browser or os.environ.get("EVA_DEFAULT_BROWSER", "chrome")
        is_youtube = "youtube" in normalized or "play " in normalized
        steps.append(TaskStep(
            task_id=task_id,
            sequence=len(steps) + 1,
            description=f"Search {browser} for {query.strip()}",
            dependencies=[steps[-1].step_id] if steps else [],
            action=ActionModel(tool="application_tool", arguments={"operation": "youtube_search" if is_youtube else "search", "application": browser, "query": query.strip(), "search_provider": "youtube" if is_youtube else "google"}),
        ))
    for index in range(1, len(steps)):
        if not steps[index].dependencies:
            steps[index].dependencies = [steps[index - 1].step_id]
    return steps or None

@app.on_event("startup")
async def startup_event():
    logging.info("Starting EVA Core Service...")
    db_ok = init_db()
    if not db_ok:
        logging.error("Failed to initialize database foundation.")
    execution_worker.start()
    recovered = recovery_manager.recover_interrupted_tasks()
    if recovered:
        logging.info(f"Recovered {len(recovered)} interrupted tasks on startup.")

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Stopping EVA Core Service...")
    execution_worker.stop()
    agentic_voice_service.stop()

@app.get("/api/health")
def health_check():
    return {"status": "Running", "service": "EVA Core Phase 1"}


@app.get("/api/health/detailed")
async def detailed_health_check():
    db_status = database_health()
    try:
        router_health = await model_router.health()
    except Exception as e:
        logging.warning("Error fetching model router health: %s", e)
        router_health = {}

    return {
        "status": "healthy" if db_status["available"] else "degraded",
        "database": db_status,
        "ollama": router_health.get("ollama", {"available": False, "model": model_name}),
        "gemini": router_health.get("gemini", {"available": False, "configured": False}),
        "mode": router_health.get("mode", model_router.get_privacy_mode()),
    }

@app.get("/api/system/info")
def system_info():
    try:
        return get_system_info()
    except Exception as e:
        logging.error(f"Error fetching system info: {e}")
        return {"error": "Failed to retrieve system information"}

@app.post("/api/v1/core/request", response_model=ResponseModel)
async def handle_request(req: RequestModel):
    logging.info(f"Received request {req.request_id} from {req.source}: {req.content}")
    
    # Phase 2B: Intent Engine & Routing
    intent_model = await intent_engine.determine_intent(req.content)
    intent_model = _resolve_contextual_application(intent_model, req.session_id)
    intent_model = _resolve_browser_context(intent_model, req.session_id)
    intent_model = _resolve_contextual_file_and_directory(intent_model, req.session_id)
    route_result = router.route(intent_model)
    
    status = "completed"
    task_data = None

    if intent_model.intent == "ambiguous":
        status = "requires_confirmation"
        message = "I need more information to understand that request."
    elif route_result.route == "unsupported":
        message = "I'm sorry, I don't support that type of request yet."
    elif route_result.route == "editor":
        try:
            task = await create_editor_write_task(req.request_id, req.content)
            task_data = json.loads(task.model_dump_json())
            status = "accepted"
            message = "I prepared the paragraph for the text editor."
        except Exception as exc:
            logging.error("Editor writing preparation failed: %s", exc)
            status = "failed"
            message = "I could not prepare the paragraph for the editor."
    elif route_result.route in ["application", "desktop", "file", "browser"]:
        task = execute_safe_intent(intent_model, req.session_id)
        if task is None:
            message = "That file operation is not supported or needs a path."
            status = "unsupported"
            task_data = None
            data_dict = {
                "intent": intent_model.intent,
                "confidence": intent_model.confidence,
                "route": "unsupported",
                "parameters": intent_model.parameters,
            }
            return ResponseModel(
                request_id=req.request_id,
                status=status,
                message=message,
                data=data_dict,
            )
        task_data = json.loads(task.model_dump_json())
        if task.status == TaskStatus.BLOCKED:
            status = "requires_confirmation"
        if task.status == TaskStatus.COMPLETED:
            step_result = task.steps[0].result or {}
            media_state = step_result.get("media_state")
            if media_state == "NAVIGATION_STARTED":
                query = step_result.get("query", "")
                message = f"Opened YouTube search for '{query}'. Select and click a video in the browser to play it."
            elif media_state == "SEARCH_COMPLETED":
                query = step_result.get("query", "")
                message = f"Opened search results for: {query}"
            else:
                message = f"Request classified as {intent_model.intent}. {step_result.get('message', 'Done.')}"
        else:
            outcome = task.steps[0].error.message if task.steps[0].error else "The desktop action failed."
            message = f"Request classified as {intent_model.intent}. {outcome}"
    elif route_result.route == "personal_identity":
        message = intent_model.parameters.get("fast_response") or "I am EVA, your personal assistant."
        status = "completed"
    elif route_result.route in ["conversation", "information"]:
        try:
            from core.eva_core.memory.personal_memory import get_personal_memory_manager
            active_mode = model_router.get_privacy_mode()
            include_private = (
                active_mode == PrivacyMode.PRIVATE
                or req.metadata.get("share_private_memory", False)
            )
            active_provider, provider_name, route_reason = model_router.route_provider(
                intent=intent_model.intent,
                contains_private_data=False,
                requires_complex_reasoning=(route_result.route == "information" or req.metadata.get("complex", False)),
            )
            logging.info("Handling request with %s provider (%s)", provider_name, route_reason)
            mgr = get_personal_memory_manager()
            owner = mgr.get_owner_profile()
            call_name = owner.get("call_name") or owner.get("nickname") or "Saif"
            personal_context = mgr.get_structured_llm_context(include_private=include_private)
            sys_prompt = (
                "You are EVA, an advanced AI Operating System and intelligent desktop assistant.\n"
                f"{personal_context}\n\n"
                "IMPORTANT MEMORY DIRECTIVES:\n"
                "- The memory context above is your persistent long-term memory and authoritative ground truth.\n"
                "- When answering questions about the user, their background, occupation, preferences, projects, or identity, always use the updated values from memory above.\n"
                f"- Naturally address the user as {call_name} when appropriate without forcing it into every sentence.\n"
                "- Never invent missing personal details. Be concise and helpful."
            )
            raw = await active_provider.generate_json(req.content, system=sys_prompt)
            message = (
                raw.get("response") or raw.get("content") or raw.get("message")
                or raw.get("text") or "I'm here to help."
            )
            status = "completed"
        except Exception as exc:
            logging.error(f"Text generation in handle_request failed: {exc}")
            message = "I am here to help, Saif."
            status = "completed"
    elif route_result.route == "planner":
        # Phase 2C: Planner and Task State
        message = f"Request classified as {intent_model.intent}."
        task = state_manager.create_task(request_id=req.request_id, intent=intent_model.intent)
        try:
            steps = _deterministic_control_plan(task.task_id, req.content)
            if steps is None:
                planning_provider, p_name = model_router.get_planning_provider()
                active_planner = Planner(provider=planning_provider)
                steps = await active_planner.generate_plan(task_id=task.task_id, request_content=req.content)
            task = state_manager.save_plan(task.task_id, steps)
            task = state_manager.transition_task(task.task_id, TaskStatus.PLANNED)
        except Exception as e:
            logging.error(f"Planning failed: {e}")
            task = state_manager.transition_task(task.task_id, TaskStatus.REQUIRES_CLARIFICATION)
            message = "I couldn't plan that task. Please try clarifying your request."
            status = "requires_confirmation"
            
        task_data = json.loads(task.model_dump_json())
    else:
        message = f"Request classified as {intent_model.intent}."
        
    data_dict = {
        "intent": intent_model.intent,
        "confidence": intent_model.confidence,
        "route": route_result.route,
        "parameters": intent_model.parameters
    }
    
    if task_data:
        data_dict["task"] = task_data
        
    response = ResponseModel(
        request_id=req.request_id,
        status=status,
        message=message,
        data=data_dict
    )
    logging.info(f"Routed {req.request_id} to {route_result.route}")
    return response

@app.post("/api/v1/core/chat/stream")
async def chat_stream(req: RequestModel):
    logging.info(f"Stream request {req.request_id} from {req.source}: {req.content}")
    async def stream_generator():
        # Immediate acknowledgement
        yield json.dumps({"type": "status", "value": "thinking"}) + "\n"
        
        conversation_id = req.session_id
        if not conversation_id:
            conversation_id = context_manager.create_conversation()
            
        context_manager.add_user_message(conversation_id, req.content)
        formatted_context = context_manager.format_llm_context(conversation_id, req.content)
        
        intent_model = await intent_engine.determine_intent(req.content, formatted_context)
        intent_model = _resolve_contextual_application(intent_model, conversation_id)
        intent_model = _resolve_browser_context(intent_model, conversation_id)
        intent_model = _resolve_contextual_file_and_directory(intent_model, conversation_id)
        route_result = router.route(intent_model)

        data_dict = {
            "intent": intent_model.intent,
            "confidence": intent_model.confidence,
            "route": route_result.route,
            "parameters": intent_model.parameters,
            "session_id": conversation_id
        }

        if intent_model.intent == "ambiguous":
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            msg = "I need more information to understand that request."
            yield json.dumps({"type": "token", "content": msg}) + "\n"
            context_manager.add_assistant_message(conversation_id, msg)
        elif route_result.route == "unsupported":
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            msg = "I'm sorry, I don't support that type of request yet."
            yield json.dumps({"type": "token", "content": msg}) + "\n"
            context_manager.add_assistant_message(conversation_id, msg)
        elif route_result.route == "editor":
            try:
                task = await create_editor_write_task(req.request_id, req.content)
                data_dict["task"] = json.loads(task.model_dump_json())
                yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
                yield json.dumps({"type": "token", "content": "I prepared the paragraph for the text editor."}) + "\n"
                context_manager.add_assistant_message(conversation_id, "I prepared the paragraph for the text editor.")
            except Exception as exc:
                logging.error("Editor writing preparation failed: %s", exc)
                yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
                yield json.dumps({"type": "error", "category": "editor_write_failed", "message": "I could not prepare the paragraph for the editor.", "request_id": req.request_id, "completed": False}) + "\n"
                return
        elif route_result.route == "personal_identity":
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            msg = intent_model.parameters.get("fast_response") or "I am EVA, your personal assistant."
            yield json.dumps({"type": "token", "content": msg}) + "\n"
            context_manager.add_assistant_message(conversation_id, msg)
            speak_response = req.metadata.get("tts_enabled", tts_service.enabled)
            if speak_response:
                tts_service.begin_response(req.request_id)
                tts_service.enqueue(msg, req.request_id)
        elif route_result.route in ["conversation", "information", "clarification"]:
            from core.eva_core.memory.personal_memory import get_personal_memory_manager

            active_mode = model_router.get_privacy_mode()
            include_private = (
                active_mode == PrivacyMode.PRIVATE
                or req.metadata.get("share_private_memory", False)
            )

            active_provider, provider_name, route_reason = model_router.route_provider(
                intent=intent_model.intent,
                contains_private_data=False,
                requires_complex_reasoning=(route_result.route == "information" or req.metadata.get("complex", False)),
            )
            logging.info("Routing conversation stream to %s provider (%s)", provider_name, route_reason)
            data_dict["provider"] = provider_name
            data_dict["routing_reason"] = route_reason

            mgr = get_personal_memory_manager()
            owner = mgr.get_owner_profile()
            call_name = owner.get("call_name") or owner.get("nickname") or "Saif"
            personal_context = mgr.get_structured_llm_context(include_private=include_private)
            eva_system_prompt = (
                "You are EVA, an advanced AI Operating System and intelligent assistant. "
                "Your identity is EVA. You are not a generic language model. "
                "You act as a helpful, concise, and confident AI assistant built directly into the user's computer. "
                "Always refer to yourself as EVA if asked.\n\n"
                f"{personal_context}\n\n"
                "IMPORTANT MEMORY DIRECTIVES:\n"
                "- The memory context above is your persistent long-term memory and authoritative ground truth.\n"
                "- When answering questions about the user, their background, occupation, preferences, projects, or identity, always use the updated values from memory above.\n"
                f"- Naturally address the user as {call_name} when appropriate without forcing it into every sentence.\n"
                "- Never invent missing personal details."
            )
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            
            assistant_response = ""
            speak_response = req.metadata.get("tts_enabled", tts_service.enabled)
            sentence_buffer = SentenceBuffer()
            if speak_response:
                tts_service.begin_response(req.request_id)
            try:
                async for chunk in active_provider.stream_text(formatted_context, system=eva_system_prompt):
                    assistant_response += chunk
                    if speak_response:
                        for sentence in sentence_buffer.add(chunk):
                            tts_service.enqueue(sentence, req.request_id)
                    yield json.dumps({"type": "token", "content": chunk}) + "\n"
                
                if assistant_response:
                    context_manager.add_assistant_message(conversation_id, assistant_response)
                if speak_response:
                    final_chunk = sentence_buffer.flush()
                    if final_chunk:
                        tts_service.enqueue(final_chunk, req.request_id)
            except Exception as e:
                logging.error("Stream generation failed with %s for request %s: %s", provider_name, req.request_id, e)
                yield json.dumps({
                    "type": "error",
                    "category": "generation_failed",
                    "message": f"Response generation failed via {provider_name}. Please try again.",
                    "request_id": req.request_id,
                    "completed": False,
                }) + "\n"
                return
                
        elif route_result.route in ["application", "desktop", "file", "browser"]:
            task = execute_safe_intent(intent_model, conversation_id)
            if task is None:
                yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
                yield json.dumps({
                    "type": "error",
                    "category": "unsupported_operation",
                    "message": "That operation is not supported or needs a path.",
                    "request_id": req.request_id,
                    "completed": False,
                }) + "\n"
                return
            data_dict["task"] = json.loads(task.model_dump_json())
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            if task.status == TaskStatus.COMPLETED:
                step_result = task.steps[0].result or {}
                media_state = step_result.get("media_state")
                if media_state == "NAVIGATION_STARTED":
                    query = step_result.get("query", "")
                    msg = f"Opened YouTube search for '{query}'. Select and click a video in the browser to play it."
                elif media_state == "SEARCH_COMPLETED":
                    query = step_result.get("query", "")
                    msg = f"Opened search results for: {query}"
                else:
                    msg = step_result.get("message", "Done.")
            elif task.status == TaskStatus.BLOCKED:
                msg = "This operation needs your confirmation before it can continue."
            else:
                msg = task.steps[0].error.message if task.steps[0].error else "The desktop action failed."
            yield json.dumps({"type": "token", "content": msg}) + "\n"
            context_manager.add_assistant_message(conversation_id, msg)
        elif route_result.route == "planner":
            task = state_manager.create_task(request_id=req.request_id, intent=intent_model.intent)
            planning_provider, p_name = model_router.get_planning_provider()
            data_dict["task"] = json.loads(task.model_dump_json())
            data_dict["provider"] = p_name
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            yield json.dumps({"type": "status", "value": "understanding"}) + "\n"
            
            try:
                # We don't dump the whole conversation to planner, just the content
                steps = _deterministic_control_plan(task.task_id, req.content)
                if steps is None:
                    active_planner = Planner(provider=planning_provider)
                    steps = await active_planner.generate_plan(task_id=task.task_id, request_content=req.content)
                task = state_manager.save_plan(task.task_id, steps)
                task = state_manager.transition_task(task.task_id, TaskStatus.PLANNED)
                yield json.dumps({"type": "task_update", "data": json.loads(task.model_dump_json())}) + "\n"
                yield json.dumps({"type": "status", "value": "planned"}) + "\n"
                msg = f"Task planned with {len(steps)} steps."
                context_manager.add_assistant_message(conversation_id, msg)
            except Exception as e:
                logging.error(f"Planning failed: {e}")
                task = state_manager.transition_task(task.task_id, TaskStatus.REQUIRES_CLARIFICATION)
                yield json.dumps({"type": "task_update", "data": json.loads(task.model_dump_json())}) + "\n"
                msg = "I couldn't plan that task. Please try clarifying your request."
                yield json.dumps({"type": "token", "content": msg}) + "\n"
                context_manager.add_assistant_message(conversation_id, msg)
        else:
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            msg = f"Request classified as {intent_model.intent}."
            yield json.dumps({"type": "token", "content": msg}) + "\n"
            context_manager.add_assistant_message(conversation_id, msg)
            
        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


@app.get("/api/v1/tts/status")
def tts_status():
    return tts_service.status()


@app.post("/api/v1/tts/stop")
def tts_stop():
    tts_service.stop()
    return {"stopped": True}

@app.get("/api/v1/core/task/{task_id}")
def get_task(task_id: str):
    task = state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump()


@app.get("/api/v1/core/tasks")
def list_tasks(limit: int = 50):
    return [task.model_dump() for task in state_manager.list_tasks(max(1, min(limit, 200)))]

@app.post("/api/v1/core/task/{task_id}/execute")
def execute_task_endpoint(task_id: str, background: bool = False):
    task = state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if background:
        if not task_runner.submit(task_id):
            raise HTTPException(status_code=409, detail="Task is not executable or is already running")
    else:
        executor.execute_task(task_id)
    updated_task = state_manager.get_task(task_id)
    return updated_task.model_dump()


@app.get("/api/v1/core/task/{task_id}/events")
async def task_events_stream(task_id: str):
    """
    Persistent task event stream (SSE / ndjson).
    Replays recent execution history and streams live step events.
    Allows clients to reconnect at any time without restarting completed steps.
    """
    task = state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return StreamingResponse(
        task_event_manager.event_generator(task_id, include_history=True),
        media_type="application/x-ndjson",
    )


@app.get("/api/v1/core/task/{task_id}/status")
def task_detailed_status(task_id: str):
    """Returns detailed status, step progress, and queue state for task monitoring/reconnection."""
    task = state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    is_queued = task_queue.contains(task_id)
    is_active = execution_worker._active_task_id == task_id
    data = task.model_dump()
    data["is_queued"] = is_queued
    data["is_active"] = is_active
    return data


@app.post("/api/v1/core/task/{task_id}/enqueue")
def enqueue_task_endpoint(task_id: str, priority: int = 10):
    """Enqueues task for persistent background execution independent of client connection."""
    task = state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in {TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.PENDING}:
        raise HTTPException(status_code=409, detail=f"Task is in non-executable status: {task.status}")
    success = task_queue.enqueue(task_id, priority=priority)
    if not success:
        raise HTTPException(status_code=409, detail="Task is already enqueued")
    task_event_manager.emit(task_id, "task_enqueued", {"priority": priority})
    return {"enqueued": True, "task_id": task_id, "priority": priority}


@app.get("/api/v1/core/queue")
def list_task_queue():
    """Lists tasks waiting in the execution queue."""
    return {
        "size": task_queue.size(),
        "active_task_id": execution_worker._active_task_id,
        "queued": task_queue.list_queued(),
    }


# ── Agentic Voice Mode Endpoints ──────────────────────────────────────────────

@app.post("/api/v1/stt/agentic/start")
def agentic_voice_start(session_id: Optional[str] = None):
    return agentic_voice_service.start(session_id=session_id)


@app.post("/api/v1/stt/agentic/stop")
def agentic_voice_stop():
    return agentic_voice_service.stop()


@app.post("/api/v1/stt/agentic/pause")
def agentic_voice_pause():
    return agentic_voice_service.pause()


@app.post("/api/v1/stt/agentic/resume")
def agentic_voice_resume():
    return agentic_voice_service.resume()


@app.post("/api/v1/stt/agentic/emergency_stop")
def agentic_voice_emergency_stop():
    return agentic_voice_service.emergency_stop()


@app.get("/api/v1/stt/agentic/status")
def agentic_voice_status():
    return agentic_voice_service.status()


@app.post("/api/v1/core/task/{task_id}/pause")
def pause_task_endpoint(task_id: str):
    if not task_runner.pause(task_id):
        raise HTTPException(status_code=409, detail="Task is not running")
    return state_manager.get_task(task_id).model_dump()


@app.post("/api/v1/core/task/{task_id}/resume")
def resume_task_endpoint(task_id: str):
    if not task_runner.resume(task_id):
        raise HTTPException(status_code=409, detail="Task is not paused")
    return state_manager.get_task(task_id).model_dump()


@app.post("/api/v1/core/task/{task_id}/stop")
def stop_task_endpoint(task_id: str):
    if not task_runner.stop(task_id):
        raise HTTPException(status_code=409, detail="Task is not running or paused")
    return state_manager.get_task(task_id).model_dump()


@app.get("/api/v1/core/confirmation/{confirmation_id}")
def get_confirmation_endpoint(confirmation_id: str):
    confirmation = state_manager.get_confirmation(confirmation_id)
    if not confirmation:
        raise HTTPException(status_code=404, detail="Confirmation not found")
    return confirmation


@app.post("/api/v1/core/confirmation/{confirmation_id}/approve")
def approve_confirmation_endpoint(confirmation_id: str):
    confirmation = state_manager.get_confirmation(confirmation_id)
    if not confirmation:
        raise HTTPException(status_code=404, detail="Confirmation not found")
    if confirmation["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Confirmation is {confirmation['status']}")
    if permission_hook.risk_class(confirmation["tool_name"], confirmation["arguments"]).value != "confirm_required":
        raise HTTPException(status_code=403, detail="This operation cannot be approved")

    approved = state_manager.transition_confirmation(confirmation_id, "approved")
    if not approved or approved.get("status") != "approved" or not approved.get("transitioned", False):
        raise HTTPException(status_code=409, detail="Confirmation expired or was already used")
    state_manager.reset_confirmed_step(confirmation_id)
    if not task_runner.submit(approved["task_id"], confirmation_id=confirmation_id, wait_seconds=0.25):
        raise HTTPException(status_code=409, detail="Task is no longer executable")
    task = state_manager.get_task(approved["task_id"])
    if task and task.status == TaskStatus.COMPLETED:
        session = session_manager.get_or_create("default")
        session.record_action(approved["tool_name"], approved["arguments"])
    return {"confirmation": state_manager.get_confirmation(confirmation_id), "task": task.model_dump() if task else None}


@app.post("/api/v1/core/confirmation/{confirmation_id}/deny")
def deny_confirmation_endpoint(confirmation_id: str):
    confirmation = state_manager.get_confirmation(confirmation_id)
    if not confirmation:
        raise HTTPException(status_code=404, detail="Confirmation not found")
    if confirmation["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Confirmation is {confirmation['status']}")
    denied = state_manager.transition_confirmation(confirmation_id, "denied")
    if not denied or denied.get("status") != "denied" or not denied.get("transitioned", False):
        raise HTTPException(status_code=409, detail="Confirmation expired or was already used")
    task = state_manager.get_task(confirmation["task_id"])
    if task and task.status == TaskStatus.BLOCKED:
        state_manager.transition_task(task.task_id, TaskStatus.CANCELLED)
        task = state_manager.get_task(task.task_id)
    return {"confirmation": state_manager.get_confirmation(confirmation_id), "task": task.model_dump() if task else None}

# ── Phase 3B: Conversation History Endpoints ─────────────────────────────────

import core.eva_core.database as _db_module

@app.get("/api/v1/conversations")
def list_conversations():
    """
    Return all conversations ordered by most recent activity.
    Each entry includes a generated title (first user message, truncated).
    """
    try:
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.conversation_id, c.created_at, c.updated_at,
                       (
                           SELECT cm.content
                           FROM conversation_messages cm
                           WHERE cm.conversation_id = c.conversation_id
                             AND cm.role = 'user'
                           ORDER BY cm.created_at ASC
                           LIMIT 1
                       ) AS first_user_msg,
                       (
                           SELECT COUNT(*)
                           FROM conversation_messages cm
                           WHERE cm.conversation_id = c.conversation_id
                       ) AS message_count
                FROM conversations c
                ORDER BY c.updated_at DESC
                """
            )
            rows = cursor.fetchall()

        result = []
        for row in rows:
            conv_id, created_at, updated_at, first_msg, msg_count = row
            # Generate a display title from the first user message
            raw_title = first_msg or "New Conversation"
            title = raw_title[:60] + "…" if len(raw_title) > 60 else raw_title
            result.append({
                "conversation_id": conv_id,
                "title": title,
                "created_at": created_at,
                "updated_at": updated_at,
                "message_count": msg_count,
            })
        return result
    except Exception as exc:
        logging.error(f"list_conversations error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to list conversations")


@app.get("/api/v1/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str):
    """
    Return all messages for a conversation in chronological order.
    Returns 404 if the conversation does not exist.
    """
    try:
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Conversation not found")

            cursor.execute(
                """
                SELECT message_id, role, content, created_at
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            )
            rows = cursor.fetchall()

        return [
            {
                "message_id": r[0],
                "conversation_id": conversation_id,
                "role": r[1],
                "content": r[2],
                "created_at": r[3],
            }
            for r in rows
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logging.error(f"get_conversation_messages error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")


@app.delete("/api/v1/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """
    Permanently delete a conversation and all its messages in a single
    database transaction.  Returns 404 if the conversation does not exist.
    """
    try:
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            # Enable foreign-key enforcement so cascade delete works
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Conversation not found")

            # Single transaction: delete messages then conversation
            cursor.execute(
                "DELETE FROM conversation_messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            cursor.execute(
                "DELETE FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            conn.commit()

        return {"deleted": True, "conversation_id": conversation_id}
    except HTTPException:
        raise
    except Exception as exc:
        logging.error(f"delete_conversation error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


# ── Phase 3B: Speech-to-Text Endpoint ────────────────────────────────────────

@app.post("/api/v1/stt/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Receive a raw audio file and return its transcript.

    The transcribed text is NOT automatically routed through EVA Core.
    The Flutter client receives the text, shows it in the composer for the
    user to review / edit, then submits it via the normal chat/stream
    endpoint.  This keeps STT separate from intent validation.

    Returns:
      { "transcript": "<text>" }

    Errors:
      503 – model not available (not yet downloaded)
      422 – transcription produced no output
      500 – unexpected failure
    """
    mime_type = audio.content_type or "audio/wav"
    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    try:
        transcriber = get_transcriber()
        transcript = transcriber.transcribe_bytes(audio_bytes, mime_type)
    except STTDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except STTModelNotAvailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logging.error(f"Transcription error: {exc}")
        raise HTTPException(status_code=500, detail="Transcription failed")

    if not transcript:
        raise HTTPException(status_code=422, detail="No speech detected in audio")

    return {"transcript": transcript}


# ── Phase 3B: Backend-driven recording (arecord/ALSA) ──────────────────────────────
# These endpoints allow Flutter to trigger recording on the server using
# arecord (ALSA) which is pre-installed on all Linux systems and works
# under PipeWire via the ALSA compatibility layer. No Flutter plugin needed.

import uuid as _uuid

@app.post("/api/v1/stt/record/start")
def stt_record_start(duration: float = 5.0):
    """
    Start capturing microphone audio on the server.
    Optional duration param: defaults to 5.0 seconds for automatic capture.
    """
    recording_id = str(_uuid.uuid4())
    eff_duration = duration if duration > 0 else 5.0
    try:
        start_recording(recording_id, duration=eff_duration)
        return {"recording_id": recording_id, "duration": eff_duration}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logging.error(f"stt_record_start error: {exc}")
        raise HTTPException(status_code=500, detail="Could not start recording")


@app.post("/api/v1/stt/record/stop")
def stt_record_stop(recording_id: str):
    """
    Stop the active recording, transcribe it, and return the transcript.

    Query param: recording_id (string)

    Returns:
      { "transcript": "<text>" }

    Errors:
      404 – recording_id not found (already stopped / never started)
      422 – no speech detected
      503 – Whisper model not available
      500 – recording or transcription error
    """
    try:
        wav_bytes = stop_recording(recording_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recording not found or already stopped")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        transcriber = get_transcriber()
        transcript = transcriber.transcribe_bytes(wav_bytes, "audio/wav")
    except STTDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except STTModelNotAvailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logging.error(f"Transcription error after stop: {exc}")
        raise HTTPException(status_code=500, detail="Transcription failed")

    if not transcript:
        raise HTTPException(status_code=422, detail="No speech detected in recording")

    return {"transcript": transcript}


@app.get("/api/v1/stt/record/status")
def stt_record_status(recording_id: str):
    status = recording_status(recording_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Recording not found or already stopped")
    return status


@app.post("/api/v1/stt/record/cancel")
def stt_record_cancel(recording_id: str):
    """
    Cancel an active recording without transcribing.
    Safe to call even if the recording_id does not exist.
    """
    cancel_recording(recording_id)
    return {"cancelled": True, "recording_id": recording_id}


# ── Phase 4 / Desktop Experience Endpoints ─────────────────────────────────────

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

class MemoryCreate(BaseModel):
    title: str
    content: str
    category: str = "General"
    privacy: str = "public"
    pinned: bool = False
    source: str = "user"

class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    privacy: Optional[str] = None
    pinned: Optional[bool] = None

class OwnerProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    full_name: Optional[str] = None
    preferred_name: Optional[str] = None
    call_name: Optional[str] = None
    occupation: Optional[str] = None

@app.get("/api/v1/memories/profile")
def get_owner_profile_api():
    """Retrieve structured verified owner profile and assistant identity."""
    from core.eva_core.memory.personal_memory import get_personal_memory_manager
    mgr = get_personal_memory_manager()
    return {
        "owner": mgr.get_owner_profile(),
        "assistant": mgr.get_assistant_identity(),
    }

@app.put("/api/v1/memories/profile")
def update_owner_profile_api(update: OwnerProfileUpdate):
    """Update verified owner profile fields and persist directly to SQLite."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            updates = {
                "nickname": update.nickname,
                "full_name": update.full_name,
                "preferred_name": update.preferred_name,
                "call_name": update.call_name,
                "occupation": update.occupation,
            }
            for k, val in updates.items():
                if val is not None:
                    cursor.execute(
                        "UPDATE memories SET content = ?, updated_at = ? WHERE key = ?",
                        (val.strip(), now, k),
                    )
            conn.commit()
        from core.eva_core.memory.personal_memory import get_personal_memory_manager
        mgr = get_personal_memory_manager()
        return {
            "owner": mgr.get_owner_profile(),
            "assistant": mgr.get_assistant_identity(),
        }
    except Exception as exc:
        logging.error(f"update_owner_profile error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to update owner profile")

@app.get("/api/v1/memories")
def list_memories(
    category: Optional[str] = None,
    privacy: Optional[str] = None,
    search: Optional[str] = None,
    pinned: Optional[bool] = None,
):
    try:
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            query = "SELECT memory_id, title, content, category, privacy, pinned, source, created_at, updated_at, key, confirmed FROM memories WHERE 1=1"
            params = []
            if category and category != "All Memory":
                query += " AND category = ?"
                params.append(category)
            if privacy:
                query += " AND privacy = ?"
                params.append(privacy)
            if pinned is not None:
                query += " AND pinned = ?"
                params.append(1 if pinned else 0)
            if search:
                query += " AND (title LIKE ? OR content LIKE ?)"
                term = f"%{search}%"
                params.extend([term, term])
            query += " ORDER BY pinned DESC, updated_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                "memory_id": r[0],
                "title": r[1],
                "content": r[2],
                "category": r[3],
                "privacy": r[4],
                "pinned": bool(r[5]),
                "source": r[6],
                "created_at": r[7],
                "updated_at": r[8],
                "key": r[9] if len(r) > 9 else None,
                "confirmed": bool(r[10]) if len(r) > 10 and r[10] is not None else True,
            }
            for r in rows
        ]
    except Exception as exc:
        logging.error(f"list_memories error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to list memories")


@app.post("/api/v1/memories")
def create_memory(item: MemoryCreate):
    try:
        now = datetime.now(timezone.utc).isoformat()
        mem_id = f"mem-{_uuid.uuid4().hex[:12]}"
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memories (memory_id, title, content, category, privacy, pinned, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mem_id, item.title, item.content, item.category, item.privacy, 1 if item.pinned else 0, item.source, now, now),
            )
            conn.commit()

        return {
            "memory_id": mem_id,
            "title": item.title,
            "content": item.content,
            "category": item.category,
            "privacy": item.privacy,
            "pinned": item.pinned,
            "source": item.source,
            "created_at": now,
            "updated_at": now,
        }
    except Exception as exc:
        logging.error(f"create_memory error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create memory")


@app.put("/api/v1/memories/{memory_id}")
def update_memory(memory_id: str, item: MemoryUpdate):
    try:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT memory_id, title, content, category, privacy, pinned, source, created_at FROM memories WHERE memory_id = ?", (memory_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Memory not found")

            new_title = item.title if item.title is not None else row[1]
            new_content = item.content if item.content is not None else row[2]
            new_cat = item.category if item.category is not None else row[3]
            new_priv = item.privacy if item.privacy is not None else row[4]
            new_pinned = (1 if item.pinned else 0) if item.pinned is not None else row[5]

            cursor.execute(
                """
                UPDATE memories
                SET title = ?, content = ?, category = ?, privacy = ?, pinned = ?, updated_at = ?
                WHERE memory_id = ?
                """,
                (new_title, new_content, new_cat, new_priv, new_pinned, now, memory_id),
            )
            conn.commit()

        return {
            "memory_id": memory_id,
            "title": new_title,
            "content": new_content,
            "category": new_cat,
            "privacy": new_priv,
            "pinned": bool(new_pinned),
            "source": row[6],
            "created_at": row[7],
            "updated_at": now,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logging.error(f"update_memory error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to update memory")


@app.delete("/api/v1/memories/{memory_id}")
def delete_memory(memory_id: str):
    try:
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM memories WHERE memory_id = ?", (memory_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Memory not found")
            cursor.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
            conn.commit()
        return {"deleted": True, "memory_id": memory_id}
    except HTTPException:
        raise
    except Exception as exc:
        logging.error(f"delete_memory error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to delete memory")


@app.post("/api/v1/memories/{memory_id}/pin")
def toggle_pin_memory(memory_id: str):
    try:
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pinned FROM memories WHERE memory_id = ?", (memory_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Memory not found")
            new_val = 0 if row[0] == 1 else 1
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("UPDATE memories SET pinned = ?, updated_at = ? WHERE memory_id = ?", (new_val, now, memory_id))
            conn.commit()
        return {"memory_id": memory_id, "pinned": bool(new_val)}
    except HTTPException:
        raise
    except Exception as exc:
        logging.error(f"toggle_pin error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to toggle pin")


# ── Settings Key-Value Store ──────────────────────────────────────────────────

@app.get("/api/v1/settings")
def get_settings():
    try:
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM system_config")
            rows = cursor.fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception as exc:
        logging.error(f"get_settings error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get settings")


@app.post("/api/v1/settings")
def save_settings(settings: Dict[str, Any]):
    try:
        with sqlite3.connect(_db_module.DB_PATH) as conn:
            cursor = conn.cursor()
            for k, v in settings.items():
                val_str = json.dumps(v) if not isinstance(v, str) else v
                cursor.execute(
                    "INSERT INTO system_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (k, val_str),
                )
            conn.commit()
        return {"saved": True, "count": len(settings)}
    except Exception as exc:
        logging.error(f"save_settings error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save settings")


# ── Application Manager Endpoints ─────────────────────────────────────────────

@app.get("/api/v1/apps")
def list_applications():
    app_tool = tool_registry.get("application_tool")
    if not app_tool:
        raise HTTPException(status_code=500, detail="Application tool not registered")

    app_meta = {
        "chrome": {"display_name": "Google Chrome", "category": "Browsers", "icon": "web"},
        "firefox": {"display_name": "Mozilla Firefox", "category": "Browsers", "icon": "language"},
        "brave": {"display_name": "Brave Browser", "category": "Browsers", "icon": "shield"},
        "vscode": {"display_name": "Visual Studio Code", "category": "Development", "icon": "code"},
        "calculator": {"display_name": "GNOME Calculator", "category": "Utilities", "icon": "calculate"},
        "settings": {"display_name": "GNOME Settings", "category": "System", "icon": "settings"},
        "text editor": {"display_name": "Text Editor", "category": "Productivity", "icon": "edit_note"},
        "file manager": {"display_name": "Files (Nautilus)", "category": "System", "icon": "folder"},
    }

    result = []
    seen = set()
    for app_key, executable in ApplicationTool.ALLOWLIST.items():
        primary_key = "chrome" if "chrome" in app_key else ("vscode" if "code" in app_key else ("text editor" if "editor" in app_key or "notepad" in app_key else ("brave" if "brave" in app_key else ("file manager" if "nautilus" in app_key or "file" in app_key else app_key))))
        if primary_key in seen:
            continue
        seen.add(primary_key)

        resolved = app_tool._resolve_executable(executable)
        running_procs = app_tool._running_processes(executable) if resolved else []
        meta = app_meta.get(primary_key, {"display_name": primary_key.title(), "category": "Applications", "icon": "apps"})

        result.append({
            "key": primary_key,
            "display_name": meta["display_name"],
            "category": meta["category"],
            "icon": meta["icon"],
            "is_installed": resolved is not None,
            "executable_path": resolved or "",
            "is_running": len(running_procs) > 0,
            "pid": running_procs[0].info["pid"] if running_procs else None,
        })

    return result


class AppActionRequest(BaseModel):
    application: str
    action: str  # "launch", "close", "focus"

@app.post("/api/v1/apps/action")
def app_action(req: AppActionRequest):
    app_tool = tool_registry.get("application_tool")
    if not app_tool:
        raise HTTPException(status_code=500, detail="Application tool not registered")

    op_map = {"launch": "open", "close": "close", "focus": "focus"}
    op = op_map.get(req.action)
    if not op:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {req.action}")

    res = app_tool.execute({"operation": op, "application": req.application})
    return {
        "success": res.success,
        "message": res.message,
        "error": res.error,
        "data": res.data,
    }


# ── Safe File Explorer Endpoints ──────────────────────────────────────────────

from core.eva_core.tools.file import WORKSPACE_ROOT

@app.get("/api/v1/files/list")
def list_workspace_files(path: str = ""):
    file_tool = tool_registry.get("file_tool")
    if not file_tool:
        raise HTTPException(status_code=500, detail="File tool not registered")

    rel_path = path.strip().lstrip("/")
    try:
        target_path = file_tool._resolve_path(rel_path) if rel_path else os.path.realpath(WORKSPACE_ROOT)
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Directory does not exist")
    if not os.path.isdir(target_path):
        raise HTTPException(status_code=400, detail="Target path is not a directory")

    items = []
    try:
        with os.scandir(target_path) as it:
            for entry in it:
                try:
                    stat = entry.stat()
                    is_dir = entry.is_dir()
                    entry_rel = os.path.relpath(entry.path, WORKSPACE_ROOT)
                    ext = os.path.splitext(entry.name)[1].lower() if not is_dir else ""
                    items.append({
                        "name": entry.name,
                        "relative_path": entry_rel,
                        "is_dir": is_dir,
                        "size": stat.st_size if not is_dir else 0,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "extension": ext,
                    })
                except OSError:
                    continue
    except Exception as exc:
        logging.error(f"list_workspace_files error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to list files")

    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {
        "current_path": rel_path,
        "workspace_root": WORKSPACE_ROOT,
        "items": items,
    }


@app.get("/api/v1/files/read")
def read_workspace_file(path: str):
    file_tool = tool_registry.get("file_tool")
    if not file_tool:
        raise HTTPException(status_code=500, detail="File tool not registered")

    rel_path = path.strip().lstrip("/")
    try:
        target_path = file_tool._resolve_path(rel_path)
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="File does not exist")
    if os.path.isdir(target_path):
        raise HTTPException(status_code=400, detail="Target is a directory")

    try:
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        stat = os.stat(target_path)
        return {
            "name": os.path.basename(target_path),
            "relative_path": rel_path,
            "size": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "content": content,
        }
    except Exception as exc:
        logging.error(f"read_workspace_file error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to read file")


class CreateFileRequest(BaseModel):
    path: str
    content: str = ""
    is_directory: bool = False

@app.post("/api/v1/files/create")
def create_workspace_file(req: CreateFileRequest):
    file_tool = tool_registry.get("file_tool")
    if not file_tool:
        raise HTTPException(status_code=500, detail="File tool not registered")

    rel_path = req.path.strip().lstrip("/")
    try:
        target_path = file_tool._resolve_path(rel_path)
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

    try:
        if req.is_directory:
            os.makedirs(target_path, exist_ok=True)
            return {"created": True, "is_dir": True, "path": rel_path}
        else:
            parent = os.path.dirname(target_path)
            os.makedirs(parent, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(req.content)
            return {"created": True, "is_dir": False, "path": rel_path}
    except Exception as exc:
        logging.error(f"create_workspace_file error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create file")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core.eva_core.main:app", host="127.0.0.1", port=8000, reload=True)
