#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "Setting up EVA AI OS environment..."

cd "$PROJECT_ROOT"

# Setup Python Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv --without-pip
    echo "Installing pip..."
    source venv/bin/activate
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3
fi

echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn psutil pytest httpx pydantic python-multipart

echo "Checking optional local AI services..."
if command -v ollama >/dev/null 2>&1; then
    model="${EVA_INTENT_MODEL:-llama3.2:3b}"
    if curl --silent --fail http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        echo "Ollama is reachable. Ensure model '${model}' is already installed."
    else
        echo "Ollama is installed but not reachable; classification will degrade to clarification."
    fi
else
    echo "Ollama is optional and was not found. Install it separately for local LLM support."
fi

if command -v flutter >/dev/null 2>&1; then
    echo "Installing Flutter dependencies..."
    (cd desktop/eva_desktop && flutter pub get)
else
    echo "Flutter SDK was not found. Install it separately for the desktop client."
fi

echo "Optional speech dependencies are documented in docs/development/setup.md."

echo "Setup complete."
