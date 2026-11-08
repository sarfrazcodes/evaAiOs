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

for _ in {1..20}; do
    if curl --silent --fail http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
        break
    fi
    sleep 0.25
done

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "EVA Core failed to start."
    exit 1
fi

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
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FLUTTER_PID" 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

wait
