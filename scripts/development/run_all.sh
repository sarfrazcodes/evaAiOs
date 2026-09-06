#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "Starting EVA AI OS..."

# Start backend
cd "$PROJECT_ROOT"
source venv/bin/activate
echo "Starting EVA Core Service..."
uvicorn core.eva_core.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

sleep 2 # wait for backend to start

# Start Flutter Desktop
echo "Starting EVA Desktop Shell..."
cd "$PROJECT_ROOT/desktop/eva_desktop"
if [ -d "$HOME/.local/share/flutter/bin" ]; then
    export PATH="$HOME/.local/share/flutter/bin:$PATH"
fi
flutter run -d linux &
FLUTTER_PID=$!

echo "Press Ctrl+C to stop all services."

cleanup() {
    echo "Stopping EVA AI OS..."
    kill $BACKEND_PID 2>/dev/null
    kill $FLUTTER_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

wait
