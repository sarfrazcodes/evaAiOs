# EVA AI OS

> **Development status: Version 3 — Work in Progress**  
> EVA is an experimental AI-native Linux operating environment. This repository currently focuses on the foundational system architecture; advanced AI and voice-assistant capabilities are planned for later development phases.

EVA AI OS aims to bring a conversational interface closer to the operating system, with a future vision of helping users manage tasks, interact with local system services, and work across local and cloud environments.

**Repository:** https://github.com/sarfrazcodes/evaAiOs

## Current Development Phase

This repository documents **Phase 1: Foundation and Architecture**.

The current focus is on establishing the building blocks required for a future AI operating environment:

- A Linux-oriented development environment.
- A Flutter desktop shell for the user interface.
- Python services for system integration and core functionality.
- A local SQLite database foundation.
- A controlled boundary between the desktop interface and system-level services.
- Documentation, setup scripts, and automated tests to support development.

**Important:** The current Phase 1 scope does not yet include a complete AI assistant, voice interaction, or LLM-powered task execution. These are longer-term goals, not features that should be assumed to work in the current version.

## Vision

EVA is being developed toward an operating environment where users can eventually interact with their computer more naturally and delegate supported tasks through a conversational interface.

The longer-term direction includes:

- Natural-language interaction.
- Voice input and spoken responses.
- Personal memory and context.
- Controlled desktop and operating-system actions.
- Integration with local and cloud AI models.
- A modular architecture that can grow through staged development.

These items describe the project's direction and should not be interpreted as already implemented features.

## Architecture at a Glance

The repository is organized into separate components so the desktop interface, core logic, and system integration can evolve independently.

| Component | Responsibility |
|---|---|
| `desktop/eva_desktop/` | Flutter-based desktop interface |
| `core/eva_core/` | Python core/backend functionality |
| `system/eva_system/` | System information and integration tools |
| `os/services/` | Operating-system service integration |
| `docs/` | Architecture and development documentation |
| `scripts/` | Development and setup scripts |
| `tests/` | Automated tests |

The project also includes a local SQLite foundation for future persistence needs.

## Repository Structure

```text
evaAiOs/
├── core/
│   └── eva_core/          # Python core services
├── desktop/
│   └── eva_desktop/       # Flutter desktop shell
├── docs/                  # Setup and architecture documentation
├── os/
│   └── services/          # OS-level service integration
├── scripts/               # Development and setup scripts
├── system/
│   └── eva_system/        # System information and integration
├── tests/                 # Automated tests
└── README.md
```

## Getting Started

EVA is an actively evolving project, so setup requirements and commands may change between versions. Before running the project, review the setup and architecture documentation in the repository.

### Prerequisites

The expected development environment includes:

- A Linux environment.
- Python and the project's required Python dependencies.
- Flutter and Dart for the desktop application.
- SQLite support.
- Any additional system packages listed in the project setup documentation.

### 1. Clone the repository

```bash
git clone https://github.com/sarfrazcodes/evaAiOs.git
cd evaAiOs
```

### 2. Read the setup documentation

Review the development setup guide:

```text
docs/development/setup.md
```

Follow its instructions for installing dependencies and configuring the development environment.

### 3. Review the architecture

The architecture overview is documented at:

```text
docs/architecture/overview.md
```

Use the guide to understand how the desktop, core, and system components are intended to interact.

### 4. Run the relevant components

Use the commands documented for each component in the repository. Because the project is still under active development, this README intentionally avoids inventing launch commands that may not match the current implementation.

## Development Principles

- **Modularity:** Keep desktop UI, core functionality, and system integration separated.
- **Controlled system access:** Keep a clear boundary between user-interface requests and system-level operations.
- **Incremental development:** Build and test the foundation before adding more complex AI capabilities.
- **Local foundation:** Establish local persistence and system integration before expanding the architecture.
- **Documentation and testing:** Maintain setup instructions and tests as components evolve.

## Roadmap

The roadmap below describes intended direction, not a guarantee that each feature is already implemented.

### Phase 1 — Foundation
- Establish the repository structure and component boundaries.
- Build the Flutter desktop shell.
- Set up Python core and system-integration modules.
- Establish the SQLite foundation.
- Add documentation and tests.

### Future phases — AI capabilities
Potential future work includes:

- LLM integration and intent interpretation.
- Voice-based interaction.
- Personal memory and contextual assistance.
- Desktop automation and file operations.
- Local/cloud model routing.
- Permission checks, confirmations, and safeguards for system actions.

Specific milestones may change as the project develops.

## Safety and Security

Operating-system integration requires careful handling. As EVA grows:

- Destructive or sensitive actions should require clear authorization and, where appropriate, user confirmation.
- Secrets and API keys must not be committed to the repository.
- AI-generated commands should not be executed blindly.
- System services should use the minimum permissions needed.
- User data and stored context should be handled deliberately and documented.

## Contributing

EVA is a work in progress. If you want to contribute:

1. Review the existing architecture and setup documentation.
2. Keep changes focused on a specific component or milestone.
3. Add or update tests where appropriate.
4. Update documentation when behavior or setup changes.
5. Describe the change and how it was tested in your pull request.

## Project Status

EVA AI OS is currently an experimental project under active development. The current repository is a foundation for the broader vision, not a finished operating system or a fully functional AI assistant.

The README will evolve as new phases are implemented and verified.

## License

Check the repository for a license file before reusing or redistributing this project. If no license is present, do not assume that the code is licensed for reuse.
