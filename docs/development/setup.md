# Development Setup

This guide explains how to set up the Phase 1 environment for EVA AI OS.

## Requirements
- Ubuntu 24.04/26.04 (or similar Linux distribution)
- `python3`, `git`, `curl`

## Initial Setup

1. **Clone the Repository**
   ```bash
   git clone <repository_url> evaAiOs
   cd evaAiOs
   ```

2. **Install Dependencies**
   Run the automated setup script. This script will initialize a Python virtual environment (`venv`) and install pip and necessary Python packages.
   ```bash
   ./scripts/setup/install_deps.sh
   ```

3. **Install Flutter (if not present)**
   The project requires the Flutter Linux Desktop SDK. 
   ```bash
   git clone https://github.com/flutter/flutter.git -b stable ~/.local/share/flutter
   export PATH="$HOME/.local/share/flutter/bin:$PATH"
   flutter config --enable-linux-desktop
   ```

## Running Locally

To launch both the Python backend core service and the Flutter desktop shell:

```bash
./scripts/development/run_all.sh
```

- The Python API will start on `http://127.0.0.1:8000`
- The Flutter application will compile and launch natively.
- Press `Ctrl+C` to terminate both services gracefully.

## Running Tests

To verify the backend system integrations:

```bash
source venv/bin/activate
pytest tests/test_backend.py
```
