# Phase 2E Integration

This document outlines the end-to-end integration for the EVA AI OS Core system as established in Phase 2E.

## End-to-End Flow

### 1. Request Handling
The Flutter desktop UI transmits user inputs to `POST /api/v1/core/request`.
- The `RequestModel` parses the input.
- The request content is passed to the `IntentEngine`.

### 2. Intent Determination
- **Fast Path**: `IntentEngine._evaluate_fast_path` attempts to match known deterministic strings (e.g., "hello eva!", "open chrome"). It properly strips punctuation to ensure robust matching and returns immediately with 1.0 confidence.
- **LLM Fallback**: If the fast path yields no match, it falls back to `OllamaProvider`.
- **Degradation**: If Ollama is unavailable, the fallback gracefully catches exceptions and yields `IntentModel(intent="ambiguous", confidence=0.0)`.

### 3. Routing
The `Router` determines the correct subsystem:
- Deterministic fast paths like `"conversation"`, `"application_operation"`, or `"file_operation"` route to their respective explicit execution chains.
- `complex_task` triggers the `Planner`.
- Low-confidence intents (< 0.6) map to `"clarification"`.

### 4. Planning (Complex Tasks)
If routed to the Planner, the backend attempts to construct a multi-step `TaskPlan`.
- If Ollama is unavailable, the Planner failure is caught, and the route degrades gracefully to `requires_clarification` without crashing the backend.
- Valid plans generate a `TaskModel` and multiple `TaskStep` models with dependencies. These are saved to SQLite via `TaskStateManager`.

### 5. Execution
Planned tasks can be executed via `POST /api/v1/core/task/{task_id}/execute`.
- **Architectural Boundary**: The Executor operates entirely deterministically. 
- It evaluates steps based on the `TaskStateManager` DAG dependency requirements.
- **Action Resolution Constraint**: The Executor DOES NOT feature a secondary LLM ToolResolver. If a step lacks a valid structured `ActionModel`, it is aborted safely, shifting the task to `ACTION_RESOLUTION_REQUIRED`. 
- **Tool Registry**: Resolved tools are looked up in the deterministic `ToolRegistry` (e.g., Echo, Calculator, FileTool, ApplicationTool).
- **Permissions Hook**: `PermissionHook` provides pre-execution checks (e.g., rejecting `sudo` or `rm -rf`).

### 6. Results
- Output results (`ToolResult`) are committed as JSON natively to the SQLite state store.
- Task status shifts appropriately (`COMPLETED`, `FAILED`, `BLOCKED`, `ACTION_RESOLUTION_REQUIRED`).

## Implemented vs Planned

### IMPLEMENTED
- FastAPI Request/Response framework
- Fast Path routing for Conversation, File, Application
- Ollama-backed Intent Engine and Planner 
- SQLite Task lifecycle & persistent tracking
- Task Dependency DAG 
- Executor boundary (no implicit action resolution)
- Tool interface (BaseTool, File, Application, Calculator, Echo)
- Full End-to-End graceful failure / degradation path when LLMs are inaccessible

### PLANNED (Later Phases)
- Voice integration (STT/TTS)
- Vision and screen-awareness 
- Advanced Permission UI
- Computer/Linux deep OS interactions (Dual boot, OS ISO generation, Package Management)
- Blockchain / Vault
- Persistent Long-Term Memory (LTM)
- Firebase Cloud sync
