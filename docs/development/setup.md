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

## Phase 3C local speech

Piper is optional: text chat remains functional when it is not installed or
when no audio device is available. Install it inside the virtual environment:

```bash
pip install piper-tts
```

Download the exact `en_US-amy-medium` Piper model manually from the official
Piper voice catalogue, check that model's license before redistribution, and
set its ONNX path. No model is downloaded during EVA startup.

```bash
export EVA_TTS_ENABLED=true
export EVA_TTS_ENGINE=piper
export EVA_TTS_VOICE=en_US-amy-medium
export EVA_TTS_LANGUAGE=en
export EVA_TTS_SPEED=1.0
export EVA_TTS_MODEL_PATH="$HOME/.local/share/piper/models/en_US-amy-medium.onnx"
```

Linux playback uses `ffplay` when available and falls back to `aplay`.
Install one of them if required. The UI can disable speech per request and
stop active or queued speech through the TTS controls.

Microphone recording automatically stops after sustained silence when using
`arecord`. Tune the detector if needed:

```bash
export EVA_STT_SILENCE_RMS=450
export EVA_STT_SILENCE_SECONDS=1.4
export EVA_STT_SILENCE_GRACE=1.2
```

Manual mic stop remains available as a fallback.
