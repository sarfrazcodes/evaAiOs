# EVA Core Message Protocol

This document outlines the Phase 2A foundational communication contract for EVA Core. This internal protocol ensures that Flutter Desktop, EVA Core, and future components (Router, Planner, Executor, Voice, etc.) can communicate without architectural rewrites.

## Overview
The protocol uses JSON over HTTP for inter-process communication, defined strictly via Pydantic models in Python.

### Request Lifecycle
1. **RECEIVED**: Client sends a request to the FastAPI boundary.
2. **VALIDATED**: The request is validated against the `RequestModel` schema.
3. **PROCESSING / ACCEPTED**: The backend immediately returns a `ResponseModel` indicating receipt and acceptance.
4. **COMPLETED / FAILED**: (Future) Asynchronous updates are tracked in the database via the `TaskModel`.

## Data Models

### 1. RequestModel
Represents an incoming interaction from a client.

```json
{
  "request_id": "uuid-string",
  "session_id": null,
  "source": "desktop",
  "input_type": "text",
  "content": "Open Chrome",
  "context": {},
  "metadata": {},
  "timestamp": "2026-09-06T18:00:00Z"
}
```

### 2. ResponseModel
Represents an immediate synchronous response back to the client.

```json
{
  "request_id": "uuid-string",
  "status": "accepted",
  "message": "Action recognized.",
  "data": null,
  "error": null,
  "timestamp": "2026-09-06T18:00:01Z"
}
```

### 3. TaskModel (Foundation)
Represents a long-running background process (useful for Planner/Executor phases).

```json
{
  "task_id": "uuid-string",
  "request_id": "uuid-string",
  "status": "pending",
  "current_step": 0,
  "total_steps": 1,
  "created_at": "2026-09-06T18:00:01Z",
  "updated_at": "2026-09-06T18:00:01Z",
  "result": null,
  "error": null
}
```

### 4. ActionModel (Foundation)
Represents an actionable intent to be carried out by the Executor.

```json
{
  "tool": "application.open",
  "arguments": {
    "application": "chrome"
  }
}
```

### 5. ErrorModel
Standardized error formatting for validation, permission, or execution failures.

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Missing required field 'input_type'.",
  "details": null
}
```

## Endpoints
- **POST `/api/v1/core/request`**
  - Consumes: `RequestModel`
  - Returns: `ResponseModel`

## Future-Proofing
This standardized protocol ensures that when the AI Router and Planner are introduced (Phase 2B/2C), they simply ingest `RequestModel` objects and return `ResponseModel` / `TaskModel` objects without the Flutter GUI needing to understand the underlying AI logic.
