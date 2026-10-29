# Phase 3B — Speech-to-Text, GUI Redesign & Conversation History

## Overview

Phase 3B extends EVA AI OS with three integrated capabilities:

1. **Local Speech-to-Text** via `faster-whisper`
2. **OS-like Desktop GUI** — Graphite + Muted Teal theme
3. **Persistent Conversation History** backed by the existing SQLite database

All Phase 1, Phase 2, and Phase 3A functionality is preserved.

---

## 1. Speech-to-Text

### Engine
- **faster-whisper 1.2.1** — local, CPU-compatible, no cloud API required.
- Quantisation: `int8` (CPU-friendly).

### Configuration (environment variables)

| Variable             | Default   | Description                                |
|----------------------|-----------|--------------------------------------------|
| `EVA_WHISPER_MODEL`  | `base`    | Model size: tiny/base/small/medium/large   |
| `EVA_WHISPER_LANG`   | `en`      | BCP-47 language hint                       |
| `EVA_WHISPER_DEVICE` | `cpu`     | Compute device: `cpu` or `cuda`            |

### Model setup (manual — no auto-download on startup)
```bash
# Inside the venv
pip install faster-whisper

# The model is downloaded on first transcription request
# OR pre-downloaded with:
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu')"
```

### API endpoint
```
POST /api/v1/stt/transcribe
Content-Type: multipart/form-data
Body:   audio=<file>  (WAV, WebM, OGG, MP3, FLAC …)

Response 200:  { "transcript": "<text>" }
Response 400:  Empty audio payload
Response 422:  No speech detected
Response 503:  Model not available (not downloaded yet)
Response 500:  Unexpected failure
```

### Security
- Raw audio is **never persisted** to disk (temp file deleted immediately after transcription).
- Transcribed text is **returned to the Flutter client** for user review — it is NOT automatically routed through EVA Core.
- The user explicitly presses Send after reviewing the transcript.
- STT cannot bypass intent validation, PermissionHook, or Tool Registry.

---

## 2. Desktop GUI Redesign

### Palette
| Token         | Hex       | Usage                        |
|---------------|-----------|------------------------------|
| `bg`          | `#17191D` | App background               |
| `sidebar`     | `#202329` | Nav rail, history panel      |
| `surface`     | `#252930` | Cards, title bar, composer   |
| `inputBg`     | `#1D2026` | Text fields                  |
| `accent`      | `#78CDBD` | Selected state, buttons, CTA |
| `textPri`     | `#E8EAED` | Body text                    |
| `textSec`     | `#A1A7B0` | Labels, hints, captions      |
| `border`      | `#353A43` | Dividers, card borders       |
| `error`       | `#E57373` | Error states, delete         |
| `userMsg`     | `#1E2C2A` | User message bubble          |
| `assistMsg`   | `#1C1F26` | Assistant message bubble     |

### Key design decisions
- No excessive gradients, neon glows, or glassmorphism.
- Flat, restrained depth via borders and subtle background variation.
- Consistent 8px border radius on cards; 12px on message bubbles.
- Message bubbles asymmetric: user top-right rounded, assistant top-left rounded.
- Assistant avatar icon appears inline beside each message.
- Task cards embedded directly in message bubbles — no floating overlays.

### Navigation
All six tabs preserved: **Home · Files · Apps · Memory · Settings · EVA**.
Placeholder pages clearly labelled "planned for a future phase."
EVA tab is the default landing page.

---

## 3. Conversation History

### Backend APIs (new in Phase 3B)

```
GET    /api/v1/conversations
       → list of { conversation_id, title, updated_at, message_count }
       → sorted by updated_at DESC
       → title auto-generated from first user message (max 60 chars)

GET    /api/v1/conversations/{id}/messages
       → list of { message_id, conversation_id, role, content, created_at }
       → chronological order (ASC)
       → 404 if conversation does not exist

DELETE /api/v1/conversations/{id}
       → deletes conversation and all messages in a single SQLite transaction
       → PRAGMA foreign_keys = ON enforces referential integrity
       → 404 if conversation does not exist
```

No new database schema. Reuses the Phase 3A tables: `conversations`, `conversation_messages`.

### Frontend behaviours

| Action         | Behaviour                                                    |
|----------------|--------------------------------------------------------------|
| New Chat       | Clears local messages + session ID; does NOT delete history  |
| Open Conv.     | Loads all messages, sets `_sessionId`, ready to continue     |
| Delete Conv.   | Confirmation dialog → DELETE API → refreshes list            |
| Clear Context  | Alias of New Chat (icon in composer)                         |

### Context restoration
When a saved conversation is reopened, the active `session_id` is set. The next message sent uses that ID, and `ConversationContextManager` supplies the bounded recent context (default 12 messages) to the LLM — identical to the Phase 3A behaviour.

---

## 4. Microphone UX States

| State          | Mic button appearance               | Meaning                          |
|----------------|-------------------------------------|----------------------------------|
| `idle`         | Mic icon, grey                      | Ready to record                  |
| `recording`    | Stop icon, red                      | Recording in progress            |
| `transcribing` | Spinner, muted teal                 | Waiting for STT response         |
| `error`        | Mic-off icon, red                   | Hardware or model error          |

After successful transcription the text is placed in the composer for review. The user presses Send (or edits first).

Error banner appears below the message list with actionable instructions (e.g. model download command).

---

## 5. Streaming Compatibility

`POST /api/v1/core/chat/stream` is completely preserved.
Event types (`status`, `metadata`, `token`, `task_update`, `done`) are unchanged.
`session_id` is captured from the first `metadata` event and reused for all subsequent turns.
Typewriter animation uses a 12 ms timer; batch-drains buffer when it exceeds 40 chars.

---

## 6. Dependencies Added

```
faster-whisper==1.2.1
python-multipart==0.0.32   # required for FastAPI UploadFile
```

---

## 7. Phase 3C
Not started.
