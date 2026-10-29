"""
Phase 3B — Speech-to-Text service using faster-whisper.

Architecture:
  Flutter UI ──► POST /api/v1/stt/transcribe  ──► WhisperTranscriber
                                                       └─► faster-whisper (local CPU)
                                                       └─► returns plain text

Security contract:
  - Raw audio is NEVER persisted to disk.
  - Transcribed text is returned to the caller; it is NOT automatically
    executed — it goes through the normal EVA intent → router pipeline.
  - No cloud API is called; all inference is local.
  - Model download is NOT triggered at startup; the model must be pre-pulled
    by the user (or the endpoint returns a 503 with a clear message).

Configuration (environment variables):
  EVA_WHISPER_MODEL   – model size key (default: "base")
                        Options: tiny, base, small, medium, large-v2, large-v3
  EVA_WHISPER_LANG    – BCP-47 language hint, e.g. "en" (default: "en")
  EVA_WHISPER_DEVICE  – compute device: "cpu" or "cuda" (default: "cpu")
"""

import logging
import os
import io
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Configuration (read once at import time) ─────────────────────────────────

_MODEL_SIZE = os.environ.get("EVA_WHISPER_MODEL", "base")
_LANGUAGE   = os.environ.get("EVA_WHISPER_LANG",  "en")
_DEVICE     = os.environ.get("EVA_WHISPER_DEVICE", "cpu")

# ── Lazy-loaded transcriber ───────────────────────────────────────────────────

_transcriber: Optional["WhisperTranscriber"] = None


def get_transcriber() -> "WhisperTranscriber":
    """Return a singleton WhisperTranscriber, initialising on first call."""
    global _transcriber
    if _transcriber is None:
        _transcriber = WhisperTranscriber(
            model_size=_MODEL_SIZE,
            language=_LANGUAGE,
            device=_DEVICE,
        )
    return _transcriber


class WhisperTranscriber:
    """
    Wraps faster-whisper for local, CPU-compatible speech recognition.

    The model is loaded only when the first transcription request arrives
    (lazy loading), so application startup is never blocked.
    """

    def __init__(
        self,
        model_size: str = "base",
        language: str = "en",
        device: str = "cpu",
    ) -> None:
        self.model_size = model_size
        self.language   = language
        self.device     = device
        self._model     = None  # loaded lazily
        logger.info(
            f"WhisperTranscriber configured: model={model_size}, "
            f"lang={language}, device={device}"
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """Load the faster-whisper model; raises STTModelNotAvailableError if
        the model has not been downloaded yet."""
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:
            raise STTDependencyError(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            ) from exc

        logger.info(f"Loading Whisper model '{self.model_size}' on {self.device} …")
        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type="int8",   # CPU-friendly quantisation
            )
            logger.info("Whisper model loaded successfully.")
        except Exception as exc:
            # Typically thrown when the model files are absent from the cache.
            raise STTModelNotAvailableError(
                f"Whisper model '{self.model_size}' could not be loaded. "
                f"Please download it first. Details: {exc}"
            ) from exc

    # ── Public API ────────────────────────────────────────────────────────────

    def transcribe_bytes(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """
        Transcribe raw audio bytes and return the plain-text transcript.

        Parameters
        ----------
        audio_bytes : bytes
            Raw audio data (WAV, WebM, OGG, MP3 …).
        mime_type : str
            MIME hint used to choose the file extension for the temp file.

        Returns
        -------
        str
            Transcribed text.  Empty string if nothing was recognised.
        """
        self._load_model()

        # Write to a temporary file — faster-whisper needs a file path
        suffix = _mime_to_suffix(mime_type)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, _info = self._model.transcribe(
                tmp_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,          # skip silence
                vad_parameters={"min_silence_duration_ms": 500},
            )
            transcript = " ".join(s.text.strip() for s in segments).strip()
            logger.info(f"Transcribed {len(audio_bytes)} bytes → '{transcript[:80]}…'")
            return transcript
        finally:
            # Always clean up the temp file — no persistent audio on disk
            Path(tmp_path).unlink(missing_ok=True)


# ── Custom exceptions ─────────────────────────────────────────────────────────

class STTDependencyError(RuntimeError):
    """faster-whisper is not installed."""


class STTModelNotAvailableError(RuntimeError):
    """The requested Whisper model has not been downloaded yet."""


class STTTranscriptionError(RuntimeError):
    """Transcription failed for an unexpected reason."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mime_to_suffix(mime_type: str) -> str:
    """Map a MIME type to a file suffix for the temp file."""
    table = {
        "audio/wav":  ".wav",
        "audio/wave": ".wav",
        "audio/x-wav": ".wav",
        "audio/webm": ".webm",
        "audio/ogg":  ".ogg",
        "audio/mp4":  ".mp4",
        "audio/mpeg": ".mp3",
        "audio/flac": ".flac",
    }
    return table.get(mime_type.lower().split(";")[0].strip(), ".audio")
