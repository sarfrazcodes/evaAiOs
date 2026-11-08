import logging
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(title="EVA AI OS Core Service", version="0.1.0")

# Initialize Phase 2C components globally
model_name = os.environ.get("EVA_INTENT_MODEL", "llama3.2:3b")
llm_provider = OllamaProvider(model=model_name)
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


def execute_safe_intent(intent_model):
    init_db()
    arguments = dict(intent_model.parameters)
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
        if arguments.get("operation") not in {"create_file", "create_directory", "read_file", "list_directory"}:
            return None
        tool_name = "file_tool"
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
    return state_manager.get_task(task.task_id)


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

@app.get("/api/health")
def health_check():
    return {"status": "Running", "service": "EVA Core Phase 1"}


@app.get("/api/health/detailed")
def detailed_health_check():
    db_status = database_health()
    ollama_status = {"available": False, "model": model_name, "model_available": False}
    try:
        with httpx.Client(timeout=1.5) as client:
            response = client.get(f"{llm_provider.base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            names = {model.get("name") for model in models if isinstance(model, dict)}
            ollama_status.update({"available": True, "model_available": model_name in names})
    except (httpx.HTTPError, ValueError, TypeError):
        pass

    return {
        "status": "healthy" if db_status["available"] else "degraded",
        "database": db_status,
        "ollama": ollama_status,
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
        task = execute_safe_intent(intent_model)
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
            message = f"Request classified as {intent_model.intent}. {task.steps[0].result['message']}"
        else:
            outcome = task.steps[0].error.message if task.steps[0].error else "The desktop action failed."
            message = f"Request classified as {intent_model.intent}. {outcome}"
    elif route_result.route == "planner":
        # Phase 2C: Planner and Task State
        message = f"Request classified as {intent_model.intent}."
        task = state_manager.create_task(request_id=req.request_id, intent=intent_model.intent)
        try:
            steps = _deterministic_control_plan(task.task_id, req.content)
            if steps is None:
                steps = await planner.generate_plan(task_id=task.task_id, request_content=req.content)
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
        elif route_result.route in ["conversation", "information", "clarification"]:
            eva_system_prompt = (
                "You are EVA, an advanced AI Operating System and intelligent assistant. "
                "Your identity is EVA. You are not a generic language model. "
                "You act as a helpful, concise, and confident AI assistant built directly into the user's computer. "
                "Always refer to yourself as EVA if asked."
            )
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            
            assistant_response = ""
            speak_response = req.metadata.get("tts_enabled", tts_service.enabled)
            sentence_buffer = SentenceBuffer()
            if speak_response:
                tts_service.begin_response(req.request_id)
            try:
                async for chunk in llm_provider.stream_text(formatted_context, system=eva_system_prompt):
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
                logging.error("Stream generation failed for request %s: %s", req.request_id, e)
                yield json.dumps({
                    "type": "error",
                    "category": "generation_failed",
                    "message": "Response generation failed. Please try again.",
                    "request_id": req.request_id,
                    "completed": False,
                }) + "\n"
                return
                
        elif route_result.route in ["application", "desktop", "file", "browser"]:
            task = execute_safe_intent(intent_model)
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
                msg = task.steps[0].result["message"]
            elif task.status == TaskStatus.BLOCKED:
                msg = "This operation needs your confirmation before it can continue."
            else:
                msg = task.steps[0].error.message if task.steps[0].error else "The desktop action failed."
            yield json.dumps({"type": "token", "content": msg}) + "\n"
            context_manager.add_assistant_message(conversation_id, msg)
        elif route_result.route == "planner":
            task = state_manager.create_task(request_id=req.request_id, intent=intent_model.intent)
            data_dict["task"] = json.loads(task.model_dump_json())
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            yield json.dumps({"type": "status", "value": "understanding"}) + "\n"
            
            try:
                # We don't dump the whole conversation to planner, just the content
                steps = _deterministic_control_plan(task.task_id, req.content)
                if steps is None:
                    steps = await planner.generate_plan(task_id=task.task_id, request_content=req.content)
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
def stt_record_start():
    """
    Start capturing microphone audio on the server.
    Returns a recording_id that must be passed to /stop or /cancel.

    Returns:
      { "recording_id": "<uuid>", "recorder": "arecord | parecord | sox" }

    Errors:
      503 – no recorder binary found
      500 – unexpected error
    """
    recording_id = str(_uuid.uuid4())
    try:
        start_recording(recording_id)
        return {"recording_id": recording_id}
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core.eva_core.main:app", host="127.0.0.1", port=8000, reload=True)
