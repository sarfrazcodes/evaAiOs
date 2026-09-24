# Phase 2 Core Integration

This document outlines the end-to-end integration for the EVA AI OS Core system as established at the completion of Phase 2.

## End-to-End Flow

### 1. Request Handling & Streaming
The Flutter desktop UI transmits user inputs to `POST /api/v1/core/chat/stream`.
- This endpoint returns an NDJSON (Newline Delimited JSON) stream, yielding events like `status`, `metadata`, `token`, and `done`.
- The `RequestModel` parses the input, checking for `session_id`.
- The `ConversationContextManager` creates or retrieves a conversation, appending the user request.

### 2. Intent Determination
- **Context injection**: The `ConversationContextManager` formats recent messages and injects them into the LLM context.
- **Fast Path**: `IntentEngine._evaluate_fast_path` attempts to match known deterministic strings against raw user input. It bypasses LLM overhead and returns immediately with 1.0 confidence.
- **LLM Fallback**: If the fast path yields no match, it falls back to `OllamaProvider` with the context-aware prompt.
- **Degradation**: If Ollama is unavailable, the fallback gracefully catches exceptions and yields `IntentModel(intent="ambiguous", confidence=0.0)`.

### 3. Routing
The `Router` determines the correct subsystem:
- Deterministic fast paths like `"application_operation"`, or `"file_operation"` route to explicit execution chains.
- `"conversation"` routes to the contextual LLM stream generator, streaming tokens natively back to the UI.
- `complex_task` triggers the `Planner`.
- Low-confidence intents (< 0.6) map to `"clarification"`.

### 4. Planning (Complex Tasks)
If routed to the Planner, the backend attempts to construct a multi-step `TaskPlan`.
- If Ollama is unavailable, the Planner failure is caught, and the route degrades gracefully to `requires_clarification` without crashing the backend.
- Valid plans generate a `TaskModel` and multiple `TaskStep` models with dependencies. These are saved to SQLite via `TaskStateManager` and emitted down the NDJSON stream as `task_update` events.

### 5. Execution
Planned tasks can be executed via `POST /api/v1/core/task/{task_id}/execute`.
- **Architectural Boundary**: The Executor operates entirely deterministically. 
- It evaluates steps based on the `TaskStateManager` DAG dependency requirements.
- **Action Resolution Constraint**: The Executor DOES NOT feature a secondary LLM ToolResolver. If a step lacks a valid structured `ActionModel`, it is aborted safely, shifting the task to `ACTION_RESOLUTION_REQUIRED`. 
- **Tool Registry**: Resolved tools are looked up in the deterministic `ToolRegistry` (e.g., Echo, Calculator, FileTool, ApplicationTool).
- **Permissions Hook**: `PermissionHook` provides pre-execution checks (e.g., rejecting `sudo` or `rm -rf`).

### 6. Results & Context Storage
- Output results (`ToolResult`) are committed as JSON natively to the SQLite state store.
- For conversational flows, successful streamed LLM responses are tracked in the `ConversationContextManager` database to maintain persistent short-term multi-turn memory without polluting task data.

## Implemented vs Planned

### IMPLEMENTED
- Fast Path routing for Conversation, File, Application
- Ollama-backed Intent Engine and Planner 
- Short-Term Conversation Context Manager (SQLite bounded memory)
- High-Performance NDJSON Streaming Architecture for the Chat UI
- SQLite Task lifecycle & persistent tracking
- Task Dependency DAG 
- Executor boundary (no implicit action resolution)
- Tool interface (BaseTool, File, Application, Calculator, Echo)
- Full End-to-End graceful failure / degradation path when LLMs are inaccessible

### PLANNED (Later Phases)
- Voice integration (STT/TTS)
- Vision and screen-awareness 
- Advanced Permission UI interventions
- Computer/Linux deep OS interactions (Dual boot, OS ISO generation, Package Management)
- Blockchain / Vault
- Persistent Long-Term Memory (LTM)
- Firebase Cloud sync
