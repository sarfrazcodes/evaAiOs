import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from system.eva_system.sys_info import get_system_info
from core.eva_core.database import init_db
import sys
import os
import json

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.eva_core.protocol import RequestModel, ResponseModel, TaskStatus
from core.eva_core.llm.ollama_provider import OllamaProvider
from core.eva_core.intent.engine import IntentEngine
from core.eva_core.intent.router import Router
from core.eva_core.task.planner import Planner
from core.eva_core.task.state import TaskStateManager
from core.eva_core.executor.executor import Executor
from core.eva_core.tools.registry import ToolRegistry
from core.eva_core.permissions.hook import PermissionHook
from core.eva_core.tools.echo import EchoTool
from core.eva_core.tools.calculator import CalculatorTool
from core.eva_core.tools.file import FileTool
from core.eva_core.tools.application import ApplicationTool
from core.eva_core.context.manager import ConversationContextManager

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

tool_registry = ToolRegistry()
tool_registry.register(EchoTool())
tool_registry.register(CalculatorTool())
tool_registry.register(FileTool())
tool_registry.register(ApplicationTool())

permission_hook = PermissionHook()
executor = Executor(state_manager=state_manager, tool_registry=tool_registry, permission_hook=permission_hook)

@app.on_event("startup")
async def startup_event():
    logging.info("Starting EVA Core Service...")
    db_ok = init_db()
    if not db_ok:
        logging.error("Failed to initialize database foundation.")

@app.get("/api/health")
def health_check():
    return {"status": "Running", "service": "EVA Core Phase 1"}

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
    route_result = router.route(intent_model)
    
    status = "completed"
    task_data = None

    if intent_model.intent == "ambiguous":
        status = "requires_confirmation"
        message = "I need more information to understand that request."
    elif route_result.route == "unsupported":
        message = "I'm sorry, I don't support that type of request yet."
    elif route_result.route == "planner":
        # Phase 2C: Planner and Task State
        message = f"Request classified as {intent_model.intent}."
        task = state_manager.create_task(request_id=req.request_id, intent=intent_model.intent)
        try:
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
        elif route_result.route in ["conversation", "information", "clarification"]:
            eva_system_prompt = (
                "You are EVA, an advanced AI Operating System and intelligent assistant. "
                "Your identity is EVA. You are not a generic language model. "
                "You act as a helpful, concise, and confident AI assistant built directly into the user's computer. "
                "Always refer to yourself as EVA if asked."
            )
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            
            assistant_response = ""
            try:
                async for chunk in llm_provider.stream_text(formatted_context, system=eva_system_prompt):
                    assistant_response += chunk
                    yield json.dumps({"type": "token", "content": chunk}) + "\n"
                
                if assistant_response:
                    context_manager.add_assistant_message(conversation_id, assistant_response)
            except Exception as e:
                logging.error(f"Stream generation failed: {e}")
                
        elif route_result.route == "planner":
            task = state_manager.create_task(request_id=req.request_id, intent=intent_model.intent)
            data_dict["task"] = json.loads(task.model_dump_json())
            yield json.dumps({"type": "metadata", "data": data_dict}) + "\n"
            yield json.dumps({"type": "status", "value": "understanding"}) + "\n"
            
            try:
                # We don't dump the whole conversation to planner, just the content
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

@app.get("/api/v1/core/task/{task_id}")
def get_task(task_id: str):
    task = state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump()

@app.post("/api/v1/core/task/{task_id}/execute")
def execute_task_endpoint(task_id: str):
    task = state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    executor.execute_task(task_id)
    updated_task = state_manager.get_task(task_id)
    return updated_task.model_dump()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core.eva_core.main:app", host="127.0.0.1", port=8000, reload=True)
