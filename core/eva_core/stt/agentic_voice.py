import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
import wave
from typing import Optional, Callable, Dict, Any

import numpy as np

from core.eva_core.stt.transcriber import get_transcriber
from core.eva_core.tts.service import get_tts_service

logger = logging.getLogger(__name__)

class AgenticVoiceService:
    """Fully Agentic Voice Loop: Continuous capture, VAD, silence detection, Whisper STT, Core execution, TTS output, and echo prevention."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AgenticVoiceService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        handler_callback: Optional[Callable[[str], Any]] = None,
        silence_threshold_rms: float = 450.0,
        silence_duration: float = 1.3,
        speech_min_duration: float = 0.4,
    ):
        if getattr(self, "_initialized", False):
            if handler_callback:
                self.handler_callback = handler_callback
            return

        self.handler_callback = handler_callback
        self.silence_threshold_rms = float(os.environ.get("EVA_AGENTIC_SILENCE_RMS", silence_threshold_rms))
        self.silence_duration = float(os.environ.get("EVA_AGENTIC_SILENCE_SECONDS", silence_duration))
        self.speech_min_duration = speech_min_duration

        self._active = False
        self._paused = False
        self._listening = False
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[subprocess.Popen] = None
        self._session_id = "agentic_voice_session"

        self.last_transcript: Optional[str] = None
        self.last_response: Optional[str] = None
        self.last_error: Optional[str] = None

        self._initialized = True

    def start(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Starts continuous microphone capture and agentic loop."""
        with self._lock:
            if session_id:
                self._session_id = session_id
            if self._active:
                return self.status()
            self._active = True
            self._paused = False
            self._thread = threading.Thread(target=self._capture_loop, name="eva-agentic-voice", daemon=True)
            self._thread.start()
            logger.info("Agentic voice service started.")
            return self.status()

    def pause(self) -> Dict[str, Any]:
        with self._lock:
            self._paused = True
            logger.info("Agentic voice service paused.")
            return self.status()

    def resume(self) -> Dict[str, Any]:
        with self._lock:
            self._paused = False
            logger.info("Agentic voice service resumed.")
            return self.status()

    def stop(self) -> Dict[str, Any]:
        """Stops the continuous listening loop."""
        with self._lock:
            self._active = False
            self._listening = False
            if self._process and self._process.poll() is None:
                try:
                    self._process.terminate()
                except Exception:
                    pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Agentic voice service stopped.")
        return self.status()

    def emergency_stop(self) -> Dict[str, Any]:
        """Emergency stop: halts speech playback, recording, and pauses agentic listening."""
        logger.warning("Emergency stop triggered in AgenticVoiceService!")
        try:
            tts = get_tts_service()
            tts.stop()
        except Exception as e:
            logger.error(f"Error stopping TTS: {e}")

        with self._lock:
            self._paused = True
            self._listening = False
            if self._process and self._process.poll() is None:
                try:
                    self._process.terminate()
                except Exception:
                    pass
        return self.status()

    def status(self) -> Dict[str, Any]:
        tts = get_tts_service()
        tts_speaking = tts.status().get("speaking", False)
        return {
            "active": self._active,
            "paused": self._paused,
            "listening": self._listening and not tts_speaking and not self._paused,
            "tts_speaking": tts_speaking,
            "silence_threshold": self.silence_threshold_rms,
            "session_id": self._session_id,
            "last_transcript": self.last_transcript,
            "last_response": self.last_response,
            "last_error": self.last_error,
        }

    def _resolve_recorder_cmd(self) -> list[str]:
        arecord = shutil.which("arecord")
        if arecord:
            return [arecord, "-q", "-t", "raw", "-f", "S16_LE", "-r", "16000", "-c", "1"]
        raise RuntimeError("arecord is required for Linux backend audio capture.")

    def _capture_loop(self):
        """Background continuous audio streaming and speech segmentation loop."""
        chunk_samples = 1600  # 100ms @ 16kHz
        chunk_bytes = chunk_samples * 2  # 16-bit PCM

        while self._active:
            if self._paused:
                time.sleep(0.1)
                continue

            try:
                cmd = self._resolve_recorder_cmd()
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=chunk_bytes * 4
                )
            except Exception as e:
                self.last_error = f"Failed to start recorder: {e}"
                logger.error(self.last_error)
                time.sleep(1.0)
                continue

            speech_buffer = []
            speech_detected = False
            silence_start: Optional[float] = None
            speech_start: Optional[float] = None

            logger.info("Agentic voice listening for speech...")
            self._listening = True

            while self._active and not self._paused:
                tts = get_tts_service()
                # Echo prevention: If TTS is speaking, drop incoming audio and discard buffer
                if tts.status().get("speaking", False):
                    speech_buffer.clear()
                    speech_detected = False
                    silence_start = None
                    speech_start = None
                    # Drain pipe
                    if self._process and self._process.stdout:
                        try:
                            self._process.stdout.read(chunk_bytes)
                        except Exception:
                            pass
                    time.sleep(0.05)
                    continue

                if not self._process or not self._process.stdout:
                    break

                try:
                    raw = self._process.stdout.read(chunk_bytes)
                    if not raw or len(raw) < chunk_bytes:
                        break
                except Exception:
                    break

                samples = np.frombuffer(raw, dtype=np.int16)
                rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2))) if len(samples) > 0 else 0.0

                now = time.monotonic()
                is_speech = rms > self.silence_threshold_rms

                if is_speech:
                    if not speech_detected:
                        speech_detected = True
                        speech_start = now
                        logger.info(f"Speech detected (RMS: {rms:.1f})")
                    speech_buffer.append(raw)
                    silence_start = None
                elif speech_detected:
                    # Trailing silence after speech
                    speech_buffer.append(raw)
                    if silence_start is None:
                        silence_start = now
                    elif (now - silence_start) >= self.silence_duration:
                        # Completed speech segment detected!
                        duration = (now - (speech_start or now))
                        if duration >= self.speech_min_duration and speech_buffer:
                            logger.info(f"Speech utterance completed ({duration:.2f}s). Processing...")
                            full_pcm = b"".join(speech_buffer)
                            speech_buffer.clear()
                            speech_detected = False
                            silence_start = None
                            speech_start = None

                            self._process_utterance(full_pcm)
                        else:
                            speech_buffer.clear()
                            speech_detected = False
                            silence_start = None
                            speech_start = None

            # Clean up process
            if self._process and self._process.poll() is None:
                try:
                    self._process.terminate()
                except Exception:
                    pass
                self._process = None

    def _process_utterance(self, pcm_bytes: bytes):
        """Transcribes PCM bytes and invokes the agentic command handler."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(pcm_bytes)

            transcriber = get_transcriber()
            result = transcriber.transcribe(tmp_path)
            transcript = result.get("text", "").strip() if isinstance(result, dict) else ""

            if not transcript:
                logger.info("Empty transcription; resuming listening.")
                return

            self.last_transcript = transcript
            logger.info(f"Agentic voice transcript: '{transcript}'")

            # Route directly to EVA Core handler
            if self.handler_callback:
                response_text = self.handler_callback(transcript)
                self.last_response = response_text
                logger.info(f"Agentic voice response: '{response_text}'")

        except Exception as e:
            self.last_error = f"Error processing voice utterance: {e}"
            logger.error(self.last_error, exc_info=True)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
