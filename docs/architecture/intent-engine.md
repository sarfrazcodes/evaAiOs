# EVA Core Intent Engine & Router

Phase 2B introduces the first intelligence layer into EVA Core: the **Intent Engine** and **Router**. The goal of this architecture is to parse a natural language string and deterministically map it to a specific subsystem without executing any commands.

## Architecture Pipeline
```
User -> Flutter -> RequestModel -> FastAPI -> Intent Engine
    |-> Fast Path (Regex)
    \-> LLM Provider (Ollama)
-> IntentModel -> Router -> RouteResult -> ResponseModel
```

## Intent Taxonomy
The Intent Engine categorizes every request into exactly one of these intents:
- `conversation`: Greetings, general chat.
- `information_request`: Asking facts, data.
- `system_command`: Asking to change OS state (e.g. dark mode).
- `file_operation`: Asking to create, read, update, delete files.
- `application_operation`: Asking to open or close an application.
- `browser_operation`: Asking to browse the web.
- `document_operation`: Asking to manipulate a document.
- `complex_task`: A request that requires a multi-step Planner.
- `unsupported`: Something structurally impossible currently.
- `ambiguous`: Too little context to decide.

## Models
### IntentModel
```json
{
  "intent": "application_operation",
  "confidence": 1.0,
  "reason": "Matched regex fast-path",
  "parameters": {
    "application": "chrome"
  }
}
```

### RouteResult
```json
{
  "route": "application",
  "intent": "application_operation",
  "confidence": 1.0
}
```

## LLM Provider Abstraction
Ollama is isolated behind the `LLMProvider` interface to ensure that swapping local models, or moving to a cloud LLM, does not require rewriting the Intent Engine. We use `httpx` instead of the `ollama` SDK to enforce zero arbitrary execution and tightly manage HTTP timeouts.

## Security Boundary
The LLM is explicitly barred from executing code. It is only given a text prompt and returns structured JSON intent data. The Router deterministically handles the routing based on the JSON response.
