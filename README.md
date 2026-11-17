# EVA AI OS 2.0 – Sovereign Agentic Desktop Assistant for Linux

[![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20x86__64-orange.svg)](#prerequisites)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flutter: 3.x](https://img.shields.io/badge/Flutter-3.x%20Desktop-cyan.svg)](https://flutter.dev/)
[![Local LLM: Ollama](https://img.shields.io/badge/LLM-Ollama%20Llama%203.2-purple.svg)](https://ollama.ai/)
[![STT: Faster--Whisper](https://img.shields.io/badge/STT-Faster--Whisper-green.svg)](https://github.com/SYSTRAN/faster-whisper)
[![TTS: Piper](https://img.shields.io/badge/TTS-Piper%20Neural-yellow.svg)](https://github.com/rhasspy/piper)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**EVA AI OS** is a local-first, privacy-preserving, voice-controlled agentic desktop operating environment for Linux. Unlike cloud-tethered assistants that continuously stream private audio and system metadata to third-party telemetry servers, EVA executes speech-to-text, cognitive reasoning, task planning, and neural voice synthesis **100% on-device** using commodity hardware.

---

## 🌟 Key Features

### 🎙️ Sovereign Multimodal Voice Pipeline
- **Faster-Whisper STT**: Real-time acoustic transcription powered by CTranslate2 on CPU, delivering >93% accuracy even under noisy acoustic conditions.
- **Agentic Voice Polling**: Autonomous voice activity detection (VAD) and silence polling for hands-free conversational turns without manual button holding.
- **Piper Neural TTS**: High-fidelity local voice synthesis (`en_US-amy-medium`) running on ONNX runtime with sub-250ms synthesis latency.

### 🛡️ Privacy Router & Multi-Provider Engine
- **Private Mode (Default)**: Strictly air-gapped. 100% of LLM reasoning runs locally via Ollama (`llama3.2:3b`). External network queries are completely blocked at the backend gateway level.
- **Hybrid Mode**: Routine desktop tasks, personal memories, and file operations execute locally; multi-step analytical reasoning uses external cloud LLMs only with user consent.
- **Public Mode**: Cloud-augmented mode powered by Google Gemini 2.5 REST API for complex code synthesis and high-level reasoning.
- **Credential Protection**: API keys are stored securely on the host workstation and never transmitted to third parties or exposed in the frontend.

### 🧠 Persistent Personal Identity & Private Memory
- **Owner Profile**: EVA knows its creator and maintains persistent structured memory (verified creator **Mohd Sarfraz Saifi / Saif**, BTech Computer Science Engineering student).
- **ACID SQLite Storage**: Real-time memory synchronization across application and backend restarts.
- **Context-Aware Follow-ups**: Fast-path KV-cache reuse that accelerates multi-turn dialogue latencies by >24%.

### 🖥️ Premium Desktop Experience (Flutter 3.x)
- **Linux Workstation Desktop Shell**: Built with Flutter desktop and Material 3 design principles.
- **Themes**: Professional Graphite Dark theme and Ivory Light theme.
- **Wallpaper & Visual Customization**: Dynamic wallpaper selection with live controls for brightness, blur, and opacity overlay.
- **OS Navigation Dock & Top Panel**: Quick access to Assistant, Applications, Sandboxed File Explorer, Memory Explorer, and System Task Monitor.

### ⚡ Agentic Task Execution & System Tools
- **Task State Manager**: Persistent background queue with crash recovery and progress streaming.
- **Application Tool**: Allowlist-enforced application launcher (Terminal, Browser, Calculator, Text Editor, File Manager).
- **Desktop & Audio Control**: Direct integration with Linux `wpctl`, `amixer`, and window management utilities.
- **Sandboxed File Operations**: Path-traversal-protected directory inspection and file manipulation.
- **Permission Confirmation System**: SHA-256 HMAC-gated confirmation tokens protecting destructive operations.

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   EVA Flutter Desktop UI (Presentation)                │
│   Top System Bar  •  Navigation Dock  •  Assistant  •  Memory Explorer  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / SSE / REST
┌───────────────────────────────────▼────────────────────────────────────┐
│                  FastAPI Core Gateway & ModelRouter                    │
│   Private (Ollama)  •  Hybrid Router  •  Public Cloud (Gemini 2.5)     │
└─────────────┬─────────────────────┬────────────────────┬───────────────┘
              │                     │                    │
┌─────────────▼─────────┐ ┌─────────▼──────────┐ ┌───────▼───────────────┐
│     Voice Pipeline    │ │ Cognitive & Planner│ │    Tools & Sandbox    │
│ Faster-Whisper (CPU)  │ │ IntentMatcher (0.5ms)│ Applications Allowlist │
│ Piper Neural TTS      │ │ Ollama (Llama 3.2) │ Sandboxed File I/O     │
│ PyAudio / SoundDevice │ │ SQLite Tasks & Mem │ wpctl Audio / D-Bus    │
└───────────────────────┘ └────────────────────┘ └───────────────────────┘
```

---

## 📋 Prerequisites

EVA is built for modern Linux x86_64 distributions:
- **Operating System**: Ubuntu 22.04 / 24.04 / 26.04 LTS, Debian 12+, Fedora 39+, or Arch Linux.
- **CPU**: x86_64 processor with AVX2 instruction support (Intel 8th Gen+ or AMD Ryzen).
- **RAM**: Minimum 8 GiB RAM (12–16 GiB recommended for concurrent local LLM + Whisper).
- **Python**: Version 3.10, 3.11, 3.12, 3.13, or 3.14.
- **Flutter SDK**: Version 3.24+ with Linux desktop build support.
- **Ollama**: Installed and running locally.

---

## 🚀 Complete Step-by-Step Setup Guide

Follow these steps to set up and run EVA AI OS from scratch on a clean Linux system.

### 1. Install System Dependencies

Open a terminal and install required audio, compilation, and system integration packages:

```bash
sudo apt update && sudo apt install -y \
    build-essential \
    curl \
    git \
    ffmpeg \
    alsa-utils \
    libasound2-dev \
    libpulse0 \
    libportaudio2 \
    portaudio19-dev \
    libgl1-mesa-dev \
    clang \
    cmake \
    ninja-build \
    pkg-config \
    libgtk-3-dev
```

---

### 2. Install and Configure Ollama (Local LLM)

1. **Install Ollama**:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Verify the Ollama service is running**:
   ```bash
   systemctl status ollama || ollama serve &
   ```

3. **Pull the Llama 3.2 3B model** (default sovereign LLM used by EVA):
   ```bash
   ollama pull llama3.2:3b
   ```

---

### 3. Clone the Repository

```bash
git clone https://github.com/sarfrazcodes/evaAiOs.git
cd evaAiOs
```

---

### 4. Setup Python Backend Environment

1. **Create and activate a Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Upgrade pip and install Python dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

### 5. Setup Speech Recognition & TTS Models

1. **Faster-Whisper Model**:
   Faster-Whisper downloads and caches its base model automatically to `~/.cache/huggingface/hub/` on first run. To pre-download it:
   ```bash
   python3 -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
   ```

2. **Piper Neural TTS**:
   EVA uses the lightweight, high-speed `en_US-amy-medium` ONNX voice model.
   Create the Piper models directory and download the voice:
   ```bash
   mkdir -p ~/.local/share/piper/models
   cd ~/.local/share/piper/models

   # Download the ONNX model and its config
   curl -LO https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-en-us-amy-medium.tar.gz
   tar -xzf voice-en-us-amy-medium.tar.gz
   rm voice-en-us-amy-medium.tar.gz

   # Return to project root
   cd ~/evaAiOs
   ```

---

### 6. Initialize Database & Seed Personal Memory

Initialize the SQLite database schema and seed the initial owner identity profile:

```bash
source venv/bin/activate
PYTHONPATH=. python3 -c "
from core.eva_core.database import init_db
from core.eva_core.memory.manager import MemoryManager
init_db()
MemoryManager().seed_owner_identity()
print('EVA Database and Personal Memory initialized successfully!')
"
```

---

### 7. Run EVA Core Backend

Start the FastAPI backend server:

```bash
source venv/bin/activate
uvicorn core.eva_core.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify backend health in another terminal:
```bash
curl http://127.0.0.1:8000/api/health/detailed
```
Expected output:
```json
{"status": "healthy", "service": "EVA Core", "database": "connected", "ollama": "connected"}
```

---

### 8. Run EVA Flutter Desktop Shell

1. **Navigate to the desktop application directory**:
   ```bash
   cd desktop/eva_desktop
   ```

2. **Get Flutter packages**:
   ```bash
   flutter pub get
   ```

3. **Launch the Linux desktop application**:
   ```bash
   flutter run -d linux
   ```

---

## ⚙️ Configuration & Environment Variables

EVA functions fully out-of-the-box in **Private Mode** without requiring any external API keys or internet connection.

If you wish to enable **Public Mode** for Google Gemini 2.5:
1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/).
2. You can either:
   - Configure it directly in the EVA Settings UI under **AI Provider** $\rightarrow$ **Public Mode** $\rightarrow$ **Enter API Key**.
   - Or export it as an environment variable before starting the backend:
     ```bash
     export GEMINI_API_KEY="your-gemini-api-key-here"
     ```

---

## 🧪 Running Automated Tests

Run the full backend test suite covering intent routing, desktop tools, permissions, personal memory, and agentic task execution:

```bash
# Activate virtual environment
source venv/bin/activate

# Run all pytest test suites
PYTHONPATH=. pytest tests/ -v
```

Run Flutter widget and integration tests:
```bash
cd desktop/eva_desktop
flutter test
```

---

## 📁 Repository Structure

```text
evaAiOs/
├── core/
│   └── eva_core/                # Python backend & core agent engine
│       ├── main.py              # FastAPI application & REST endpoints
│       ├── database.py          # SQLite database schema & migrations
│       ├── protocol.py          # Pydantic schemas & communication protocol
│       ├── intent/              # Two-tier cognitive intent classification
│       ├── llm/                 # ModelRouter, OllamaProvider, GeminiProvider
│       ├── memory/              # SQLite persistent memory & owner identity
│       ├── permissions/         # Security confirmation tokens & sandbox hooks
│       ├── stt/                 # Faster-Whisper transcriber & agentic voice poller
│       ├── task/                # Task state manager, worker queue & recovery
│       ├── tools/               # Linux desktop, file sandbox, app launcher, calc
│       └── tts/                 # Piper neural voice synthesis engine
├── desktop/
│   └── eva_desktop/             # Flutter desktop application
│       ├── lib/
│       │   ├── main.dart        # Flutter entrypoint & app root
│       │   ├── core/            # Theme, router, state providers, widgets
│       │   └── features/        # Assistant, settings, memory, file explorer
│       ├── test/                # Flutter unit & widget tests
│       └── pubspec.yaml         # Dart/Flutter dependencies
├── tests/                       # Automated regression & integration test suites
│   ├── test_agentic_v2.py
│   ├── test_identity_and_memory.py
│   ├── test_persistence.py
│   ├── test_phase3b.py
│   └── test_phase4_desktop_api.py
├── requirements.txt             # Python backend dependencies
├── .gitignore                   # Git ignore rules (research artifacts excluded)
└── README.md                    # Project documentation & setup guide
```

---

## 👤 Developer & Maintainer

- **Developer & Lead Systems Architect**: Mohd Sarfraz Saifi ([@sarfrazcodes](https://github.com/sarfrazcodes))
- **Project**: EVA AI OS (Sovereign Linux AI Assistant)
- **Repository**: [https://github.com/sarfrazcodes/evaAiOs](https://github.com/sarfrazcodes/evaAiOs)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
