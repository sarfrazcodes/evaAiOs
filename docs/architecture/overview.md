# Architecture Overview

The EVA AI OS is built with a strict separation of concerns, ensuring that the visual interface is decoupled from system-level privileges and AI orchestration.

## Component Stack

```
    Linux Base (Ubuntu/Debian)
        ↓
    System Layer (Privilege Abstraction)
        ↓
    EVA Core (AI Orchestration & Logic)
        ↓
    EVA Desktop (Flutter UI)
```

### 1. Desktop Shell (`desktop/eva_desktop`)
Built with Flutter for Linux Desktop. It acts as the primary user interface. It provides a visual dashboard and handles chat interactions via a seamless, high-performance streaming UI. It communicates with the system layer via local HTTP APIs (FastAPI) and NDJSON streams.

### 2. Core Service (`core/eva_core`)
A Python service providing the primary intelligence backend. Key components include:
- **Intent Engine**: A hybrid system using fast deterministic regex matching for immediate commands and falling back to a local LLM (`llama3.2:3b`) for complex/ambiguous intent classification.
- **Task Planner**: Automatically breaks down `complex_task` intents into dependency-aware execution steps.
- **Task State Manager**: SQLite-backed manager to track the lifecycle of asynchronous multi-step plans.
- **Executor & Tool Registry**: Dynamically loads tools (`FileTool`, `ApplicationTool`, etc.) and executes steps sequentially.
- **Context Manager**: An isolated short-term memory system holding recent dialogue context for accurate, multi-turn LLM understanding.
- **Permission Hook**: Intercepts high-risk actions to require explicit user verification.

### 3. System Layer (`system/eva_system`)
A collection of Python modules strictly responsible for interacting with the host Linux OS. This layer abstracts operations like hardware information retrieval, preventing the UI from executing arbitrary shell commands directly.

### 4. OS Integration (`os/`)
Contains `systemd` service templates designed to manage the lifecycle of EVA components on boot.

## Security Boundaries
- **No Root Access:** The Flutter Desktop runs as a standard user process.
- **Controlled System Execution:** The Desktop cannot run arbitrary shell commands; it must request specific data via FastAPI.
- **Execution Sandboxing**: Malicious text injections in the conversation layer are safely blocked from accessing tools by strict separation between intent processing and tool evaluation.
