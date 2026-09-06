# EVA AI OS

EVA AI OS is a next-generation AI-native Linux operating environment designed to deeply integrate with the operating system, allowing a conversational AI to understand intent, manage personal memory, and execute tasks across local and cloud environments.

## Phase 1 Overview

This repository represents **Phase 1** of the EVA AI OS project. The goal of this phase is to establish the foundational architecture, including:
- A clean Linux development environment.
- A functional Flutter-based desktop shell.
- Python system integration services providing core system capabilities.
- Local SQLite database foundation.
- A controlled boundary between the desktop UI and the system layer.

*Note: Phase 1 does not include actual AI features, voice assistants, or LLM integrations. These will be introduced in subsequent phases.*

## Repository Structure

```
eva-ai-os/
├── docs/                 # Documentation (architecture, setup)
├── os/                   # OS-level integration (systemd services)
├── desktop/              # Flutter Desktop UI (eva_desktop)
├── core/                 # Python backend services (eva_core)
├── system/               # System info & integration tools (eva_system)
├── tests/                # Automated tests
└── scripts/              # Development and setup scripts
```

## Getting Started

See `docs/development/setup.md` for instructions on setting up and running EVA AI OS locally.

## Architecture

See `docs/architecture/overview.md` for a detailed breakdown of the system components.
