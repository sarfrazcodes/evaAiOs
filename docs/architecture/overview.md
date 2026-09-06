# Architecture Overview

The EVA AI OS is built with a strict separation of concerns, ensuring that the visual interface is decoupled from system-level privileges and future AI orchestration.

## Component Stack

```
    Linux Base (Ubuntu/Debian)
        ↓
    EVA OS Platform (Python System Services)
        ↓
    EVA Desktop (Flutter UI)
        ↓
    EVA Core (API Boundary)
```

### 1. Desktop Shell (`desktop/eva_desktop`)
Built with Flutter for Linux Desktop. It acts as the primary user interface. In Phase 1, it provides a dashboard to monitor system health and navigate modules. It communicates with the system layer via local HTTP APIs (FastAPI).

### 2. Core Service (`core/eva_core`)
A Python service providing the primary backend logic. It initializes the SQLite database (`eva.db`) for future user memory, preferences, and task tracking. It exposes a local REST API that the Desktop Shell consumes.

### 3. System Layer (`system/eva_system`)
A collection of Python modules strictly responsible for interacting with the host Linux OS. This layer abstracts operations like hardware information retrieval, preventing the UI from executing arbitrary shell commands directly.

### 4. OS Integration (`os/`)
Contains `systemd` service templates designed to eventually manage the lifecycle of EVA components on boot. In Phase 1, these are provided as templates but are not actively installed.

## Security Boundaries
- **No Root Access:** The Flutter Desktop runs as a standard user process.
- **Controlled System Execution:** The Desktop cannot run arbitrary shell commands; it must request specific data via the FastAPI boundaries.
