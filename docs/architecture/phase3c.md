# Phase 3C Completion Report

## Status

The local integration is implemented and the selected Piper model is installed
in the active environment. Automated synthesis has been verified. Actual
listening through the machine's speakers remains a manual check.

## Engine and voice

- Engine: Piper TTS, loaded lazily through the optional `piper-tts` package.
- Default voice: `en_US-amy-medium`.
- Model path: `EVA_TTS_MODEL_PATH`, defaulting to
  `~/.local/share/piper/models/en_US-amy-medium.onnx`.
- The exact model is installed locally. Check the model's own license before
  bundling or redistributing it.

## Configuration and installation

```bash
source venv/bin/activate
pip install piper-tts
export EVA_TTS_ENABLED=true
export EVA_TTS_ENGINE=piper
export EVA_TTS_VOICE=en_US-amy-medium
export EVA_TTS_LANGUAGE=en
export EVA_TTS_SPEED=1.5
export EVA_TTS_MODEL_PATH="$HOME/.local/share/piper/models/en_US-amy-medium.onnx"
```

The model was downloaded with Piper's voice downloader. EVA itself never
downloads models during startup. `ffplay` is preferred for
playback, with `aplay` as a fallback. Text chat continues if either Piper, the
model, or an audio device is unavailable.

## Files changed

- `core/eva_core/tts/service.py`: lazy Piper wrapper, sentence buffer, ordered
  queue, playback, stop, status, and cleanup.
- `core/eva_core/tts/__init__.py`: TTS package exports.
- `core/eva_core/main.py`: sentence-buffered stream integration plus TTS
  status/stop endpoints and interrupted-stream error event.
- `desktop/eva_desktop/lib/main.dart`: enable/disable, speaking indicator, stop
  control, per-request preference, and audio error feedback.
- `tests/test_tts.py`: buffer, missing-model, disabled-service tests.
- `requirements.txt` and `docs/development/setup.md`: optional setup.

## Streaming behavior

The existing NDJSON token stream remains unchanged for text. Complete
punctuated sentences are queued as they arrive; remaining text is flushed when
the LLM stream completes. A single worker preserves order and prevents
overlapping playback. TTS receives only conversational response text, never
metadata or tool payloads.

The Flutter stop action clears pending audio and terminates active playback;
it does not cancel LLM generation. An interrupted LLM stream emits an error
event and is not reported as successfully complete.

## Validation

- `venv/bin/pytest -q tests/test_tts.py tests/test_chat_stream.py`: **6 passed**.
- Python syntax compilation: passed.
- Full test suite: **91 passed** with 3 existing deprecation warnings.
- Real Piper synthesis: passed with `en_US-amy-medium` at `length_scale=0.8`
  and `length_scale=0.6667`.
- Flutter analysis/tests: not run; no Flutter SDK is available on `PATH`.
- Manual audio verification: not performed through speakers.

## Known limitations

- The Piper model license still requires review before redistribution.
- Pause/resume is not exposed because the available Linux playback fallback
  only provides reliable stop behavior.
- Sentence detection is punctuation-based and intentionally conservative; it
  does not attempt full linguistic abbreviation detection.
- Performance measurements and actual CPU/memory/audio latency measurements
  remain pending manual installation and listening verification.

Phase 3D was not started.