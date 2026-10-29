# Phase 3D Completion Report

## Inspected

- Flutter chat, microphone, transcript, stream parser, and TTS controls.
- FastAPI chat stream, STT routes, TTS routes, context manager, SQLite persistence.
- Phase 2 intent matcher/router and existing planner/executor boundaries.
- Phase 3C Piper sentence buffering and playback worker.

## Changes

- `desktop/eva_desktop/lib/main.dart`: preserve partial NDJSON lines, render tokens immediately, keep generation locked until `done`, and retain the existing transcript-review flow.
- `desktop/eva_desktop/lib/main.dart`: add a voice-conversation toggle that automatically submits a non-empty transcript after recording stops; review mode remains available.
- `core/eva_core/main.py`: associate TTS chunks with each request ID and discard stale audio when a new response starts.
- `core/eva_core/tts/service.py`: response-scoped speech queueing and stale-audio cleanup.
- `core/eva_core/context/manager.py`: avoid duplicating the just-persisted user request in the LLM context.
- `core/eva_core/intent/matcher.py`: fast-path common informational questions so response generation starts without an unnecessary second intent LLM call.
- `tests/test_intent_fast_path.py` and `tests/test_tts.py`: regression coverage for fast routing, stale speech, speech cleanup, and TTS behavior.

## Unified pipeline

Typed text and reviewed STT transcripts both call the same Flutter `_sendMessage`
method and the same `POST /api/v1/core/chat/stream` endpoint. The request keeps
one `session_id`, so both modes use the same context and persistence path. STT
never executes a command directly.

The backend persists one user message and one completed assistant response.
Streaming tokens are never persisted individually. TTS receives only response
text and does not write to the conversation database.

## Streaming and speech

Flutter buffers incomplete NDJSON lines across HTTP chunks, then renders each
complete token immediately. The backend buffers punctuation-delimited speech
chunks, sends them to one ordered worker, and flushes the final remainder at
stream completion. Each chunk carries the request ID; starting another request
stops active playback and clears queued speech from the prior response.

Stop terminates current playback and clears pending audio without cancelling
LLM generation. TTS failures remain visible through status/error feedback and do
not remove generated text.

## Failure handling

Existing STT error states keep the composer usable. Empty transcripts are not
submitted. The generation lock prevents rapid duplicate sends and is released
in the request `finally` block. Backend connection and stream errors become
system messages rather than permanent loading states.

## Validation

- Complete Python suite: **96 passed**, 3 existing deprecation warnings.
- Flutter analysis: no compile/type errors; 28 existing `withOpacity`
  deprecation infos remain.
- Focused TTS, stream, context, and intent tests passed.
- Real Piper `en_US-amy-medium` synthesis/playback was previously verified.
- Manual microphone-to-chat and speaker listening checklist was not fully
  performed in this automated session.

## Manual checklist

- Typed question: automated stream path verified; physical listening pending.
- Voice question: existing STT route and transcript-review path preserved;
  physical microphone test pending.
- Follow-up context: context persistence tests pass; manual pronoun follow-up
  pending.
- Progressive speech: sentence queue is asynchronous and ordered.
- Stop: queue-clearing and response identity are covered by tests.
- Disable TTS: existing disabled-service test passes.
- Missing TTS/STT: existing graceful-failure tests and UI paths remain active.
- New conversation: session reset behavior remains unchanged.

Voice conversation mode still uses push-to-talk stop behavior. Automatic silence
detection, wake words, and full-duplex interruption are intentionally outside
Phase 3D.

No new runtime dependency was added for Phase 3D. Phase 3E and Phase 4 were
not started.
