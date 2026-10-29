"""Optional local Piper TTS with ordered sentence buffering and playback."""

from __future__ import annotations

import logging
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import wave
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_speech_text(text: str) -> str:
    """Convert user-facing Markdown into natural spoken text."""
    text = re.sub(r"```(?:\w+)?\s*", "", text)
    text = text.replace("```", "")
    text = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"(^|\s)#{1,6}\s*", r"\1", text)
    text = re.sub(r"(^|\s)[>*+-]\s+", r"\1", text)
    text = re.sub(r"__|\*\*|~~", "", text)
    text = re.sub(r"(?<!\w)[*_~](?!\w)", "", text)
    text = text.replace('"', "").replace("“", "").replace("”", "")
    text = re.sub(r"[|{}<>\\]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class SentenceBuffer:
    """Collect streamed text and release complete, user-facing sentences."""

    _boundary = re.compile(r"(?<=[.!?])(?:[\"'\u201d\u2019)]*)(?:\s+|$)")

    def __init__(self) -> None:
        self._text = ""

    def add(self, text: str) -> list[str]:
        self._text += text
        sentences = []
        while True:
            match = self._boundary.search(self._text)
            if not match:
                break
            sentence = self._text[:match.end()].strip()
            self._text = self._text[match.end():]
            if sentence:
                sentences.append(sentence)
        return sentences

    def flush(self) -> Optional[str]:
        remainder = self._text.strip()
        self._text = ""
        return remainder or None


class TTSService:
    """Lazy Piper voice wrapper with a single ordered playback worker."""

    def __init__(self) -> None:
        self.enabled = os.environ.get("EVA_TTS_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
        self.engine = os.environ.get("EVA_TTS_ENGINE", "piper").lower()
        self.voice = os.environ.get("EVA_TTS_VOICE", "en_US-amy-medium")
        self.language = os.environ.get("EVA_TTS_LANGUAGE", "en")
        self.speed = float(os.environ.get("EVA_TTS_SPEED", "1.5"))
        default_model = Path.home() / ".local" / "share" / "piper" / "models" / f"{self.voice}.onnx"
        self.model_path = Path(os.environ.get("EVA_TTS_MODEL_PATH", str(default_model))).expanduser()
        self._voice = None
        self._queue: queue.Queue[Optional[tuple[str, Optional[str]]]] = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._speaking = False
        self.last_error: Optional[str] = None
        self._initialization_failed = False
        self._active_response_id: Optional[str] = None

    def initialize(self) -> None:
        if (not self.enabled or self.engine != "piper" or self._voice is not None
                or self._initialization_failed):
            return
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Piper voice model '{self.voice}' was not found at {self.model_path}. "
                "Download the model manually and set EVA_TTS_MODEL_PATH."
            )
        try:
            from piper import PiperVoice  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Piper TTS is not installed. Run: pip install piper-tts") from exc
        self._voice = PiperVoice.load(str(self.model_path))

    def begin_response(self, response_id: str) -> None:
        """Stop and discard speech belonging to an older response."""
        self.stop()
        self._active_response_id = response_id

    def enqueue(self, text: str, response_id: Optional[str] = None) -> None:
        if self.enabled and text.strip():
            self._queue.put((text.strip(), response_id))
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._run, name="eva-tts", daemon=True)
                self._worker.start()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                return
            text, response_id = item
            try:
                self.initialize()
                if self._voice is None:
                    continue
                if response_id is not None and response_id != self._active_response_id:
                    continue
                self._speak(text)
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)
                if self._voice is None:
                    was_failed = self._initialization_failed
                    self._initialization_failed = True
                    if not was_failed:
                        logger.warning("TTS unavailable: %s", exc)
                else:
                    logger.warning("TTS playback failed: %s", exc)
            finally:
                self._queue.task_done()

    def _speak(self, text: str) -> None:
        text = normalize_speech_text(text)
        if not text:
            return
        player = shutil.which("ffplay") or shutil.which("aplay")
        if not player:
            raise RuntimeError("No audio player found. Install ffplay or alsa-utils.")
        with tempfile.NamedTemporaryFile(prefix="eva_tts_", suffix=".wav", delete=False) as audio:
            audio_path = Path(audio.name)
        try:
            with wave.open(str(audio_path), "wb") as output:
                from piper.config import SynthesisConfig  # type: ignore

                # Piper uses length scale: values below 1.0 speak faster.
                synthesis_config = SynthesisConfig(
                    length_scale=1.0 / max(0.25, min(self.speed, 4.0)),
                )
                if hasattr(self._voice, "synthesize_wav"):
                    self._voice.synthesize_wav(text, output, syn_config=synthesis_config)
                else:
                    self._voice.synthesize(text, syn_config=synthesis_config)
            command = [player, "-nodisp", "-autoexit", "-loglevel", "error", str(audio_path)] if player.endswith("ffplay") else [player, str(audio_path)]
            with self._lock:
                self._speaking = True
                self._process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return_code = self._process.wait()
            if return_code != 0:
                error = (self._process.stderr.read() or b"").decode(errors="replace").strip()
                raise RuntimeError(error or f"Audio player exited with code {return_code}")
        finally:
            with self._lock:
                self._speaking = False
                self._process = None
            audio_path.unlink(missing_ok=True)

    def stop(self) -> None:
        with self._lock:
            process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break

    def status(self) -> dict:
        with self._lock:
            speaking = self._speaking
        return {
            "enabled": self.enabled,
            "engine": self.engine,
            "voice": self.voice,
            "speed": self.speed,
            "speaking": speaking,
            "queued": self._queue.qsize(),
            "error": self.last_error,
        }

    def dispose(self) -> None:
        self.stop()
        self._queue.put(None)


_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    global _service
    if _service is None:
        _service = TTSService()
    return _service