"""
Phase 3B — Backend-driven audio recording service.

Why backend recording instead of a Flutter plugin:
  - record_linux uses `parecord` which requires PulseAudio utilities.
  - Modern Ubuntu uses PipeWire; `parecord` may not be installed.
  - `arecord` (ALSA) is always available on Linux and works under PipeWire
    via the ALSA compatibility layer.
  - Recording on the backend means zero Flutter plugin dependencies for audio.

API:
  POST /api/v1/stt/record/start   → { "recording_id": "<uuid>" }
  POST /api/v1/stt/record/stop    → triggers transcription, returns transcript
  POST /api/v1/stt/transcribe     → upload raw audio bytes (kept for testing)

Flow:
  Flutter: tap mic  → POST /start  → get recording_id
  Flutter: tap stop → POST /stop   → get { "transcript": "..." }
  Flutter: fills composer with transcript, user presses Send
"""

import logging
import os
import uuid
import subprocess
import shutil
import threading
import time
from typing import Optional, Dict

import numpy as np

logger = logging.getLogger(__name__)

# ── Active recording registry ─────────────────────────────────────────────────
# Maps recording_id → { process, wav_path }
_active_recordings: Dict[str, dict] = {}
_lock = threading.Lock()


def _monitor_silence(recording_id: str, wav_path: str) -> None:
    """Stop an ALSA WAV capture after sustained low RMS audio."""
    threshold = float(os.environ.get("EVA_STT_SILENCE_RMS", "450"))
    silence_seconds = float(os.environ.get("EVA_STT_SILENCE_SECONDS", "1.4"))
    grace_seconds = float(os.environ.get("EVA_STT_SILENCE_GRACE", "1.2"))
    started = time.monotonic()
    last_offset = 44
    silent_since: Optional[float] = None

    while True:
        time.sleep(0.2)
        with _lock:
            rec = _active_recordings.get(recording_id)
            if rec is None or rec.get("silence_detected"):
                return
            process = rec["process"]
        if process.poll() is not None:
            return
        if time.monotonic() - started < grace_seconds:
            continue
        try:
            file_size = os.path.getsize(wav_path)
            readable = file_size - last_offset
            if readable < 3200:
                continue
            readable -= readable % 2
            with open(wav_path, "rb") as audio_file:
                audio_file.seek(last_offset)
                samples = np.frombuffer(audio_file.read(readable), dtype=np.int16)
            last_offset += readable
            rms = float(np.sqrt(np.mean(np.square(samples.astype(np.float32))))) if samples.size else 0.0
            if rms < threshold:
                silent_since = silent_since or time.monotonic()
                if time.monotonic() - silent_since >= silence_seconds:
                    with _lock:
                        rec = _active_recordings.get(recording_id)
                        if rec is not None:
                            rec["silence_detected"] = True
                    process.terminate()
                    logger.info("Silence detected for recording [%s]", recording_id)
                    return
            else:
                silent_since = None
        except (FileNotFoundError, OSError, ValueError):
            return


def _find_recorder() -> Optional[str]:
    """Return the best available audio recorder binary."""
    for cmd in ("arecord", "parecord", "sox"):
        path = shutil.which(cmd)
        if path:
            return path
    return None


def start_recording(recording_id: str) -> str:
    """
    Start capturing microphone audio using arecord (ALSA).
    Returns the path to the WAV file being written to.
    Raises RuntimeError if no recorder is available.
    """
    recorder = _find_recorder()
    if not recorder:
        raise RuntimeError(
            "No audio recorder found. Install one with: sudo apt install alsa-utils"
        )

    wav_path = f"/tmp/eva_rec_{recording_id}.wav"

    recorder_name = os.path.basename(recorder)

    if recorder_name == "arecord":
        cmd = [
            recorder,
            # plughw:0,0 uses the ALSA plug layer for automatic format conversion.
            # hw:0,0 (raw hardware) is too strict and rejects 16 kHz on many codecs.
            "-D", "plughw:0,0",
            "-f", "S16_LE",      # 16-bit signed little-endian
            "-r", "16000",       # 16 kHz (Whisper native sample rate)
            "-c", "1",           # mono
            "-t", "wav",         # WAV container
            wav_path,
        ]
    elif recorder_name == "parecord":
        cmd = [
            recorder,
            "--raw",
            "--format=s16le",
            "--rate=16000",
            "--channels=1",
            wav_path,
        ]
    elif recorder_name == "sox":
        cmd = [
            recorder,
            "-d",                # default input device
            "-r", "16000",
            "-c", "1",
            "-e", "signed",
            "-b", "16",
            wav_path,
        ]
    else:
        raise RuntimeError(f"Unknown recorder: {recorder}")

    logger.info(f"Starting recording [{recording_id}] with {recorder}: {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Recorder binary not found: {recorder}") from exc

    with _lock:
        _active_recordings[recording_id] = {
            "process":  proc,
            "wav_path": wav_path,
            "recorder": recorder_name,
            "silence_detected": False,
        }

    if recorder_name == "arecord":
        threading.Thread(
            target=_monitor_silence,
            args=(recording_id, wav_path),
            name=f"eva-silence-{recording_id[:8]}",
            daemon=True,
        ).start()

    return wav_path


def recording_status(recording_id: str) -> Optional[dict]:
    with _lock:
        rec = _active_recordings.get(recording_id)
        if rec is None:
            return None
        return {
            "recording": True,
            "silence_detected": rec.get("silence_detected", False),
        }


def stop_recording(recording_id: str) -> bytes:
    """
    Stop the active recording and return the raw WAV bytes.
    Cleans up the temp file immediately.
    Raises KeyError if recording_id is not found.
    Raises RuntimeError if the recorder exited with an error.
    """
    with _lock:
        rec = _active_recordings.pop(recording_id, None)

    if rec is None:
        raise KeyError(f"No active recording with id={recording_id}")

    proc: subprocess.Popen = rec["process"]
    wav_path: str = rec["wav_path"]

    # Send SIGTERM so arecord flushes and finalises the WAV header
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    stderr_output = (proc.stderr.read() or b"").decode(errors="replace").strip()
    if stderr_output:
        # arecord always prints "Recording WAVE…" and "Aborted by signal Terminated"
        # to stderr — that is normal. Only log unexpected lines.
        unexpected = [
            l for l in stderr_output.splitlines()
            if not any(ok in l for ok in (
                "Recording WAVE", "Aborted by signal", "read error: Interrupted"
            ))
        ]
        if unexpected:
            logger.warning(f"arecord stderr [{recording_id}]: {'; '.join(unexpected)}")

    # Read the recorded WAV
    try:
        with open(wav_path, "rb") as f:
            wav_bytes = f.read()
    except FileNotFoundError:
        raise RuntimeError(
            f"Recording file not found after stop: {wav_path}. "
            f"arecord stderr: {stderr_output}"
        )
    finally:
        # Always clean up temp file
        try:
            os.unlink(wav_path)
        except OSError:
            pass

    if len(wav_bytes) < 44:          # WAV header is 44 bytes minimum
        raise RuntimeError(
            f"Recording too short ({len(wav_bytes)} bytes) — "
            f"check microphone: {stderr_output or 'no stderr output'}"
        )

    logger.info(
        f"Recording [{recording_id}] stopped. "
        f"Captured {len(wav_bytes)} bytes."
    )
    return wav_bytes


def cancel_recording(recording_id: str) -> None:
    """Terminate an active recording without returning audio."""
    with _lock:
        rec = _active_recordings.pop(recording_id, None)
    if rec is None:
        return
    proc: subprocess.Popen = rec["process"]
    wav_path: str = rec["wav_path"]
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
    try:
        os.unlink(wav_path)
    except OSError:
        pass
    logger.info(f"Recording [{recording_id}] cancelled.")
