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
pip install fastapi uvicorn psutil pytest httpx

echo "Setup complete."
