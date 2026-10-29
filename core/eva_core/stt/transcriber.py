"""
Phase 3B — Speech-to-Text service using faster-whisper.

Architecture:
  Flutter UI ──► POST /api/v1/stt/transcribe  ──► WhisperTranscriber
                                                       └─► ffmpeg (audio → PCM)
                                                       └─► faster-whisper (local CPU)
                                                       └─► returns plain text

Audio decoding strategy:
  faster-whisper normally uses soundfile for audio decoding, but soundfile has
  a Python 3.14 incompatibility (`open()` got unexpected kwarg `metadata_errors`).
  We work around this by using ffmpeg subprocess to convert any input audio format
  to raw 32-bit float PCM at 16 kHz, then passing the numpy array directly to
  faster-whisper's transcribe() method — bypassing soundfile completely.

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
import subprocess
import shutil
from typing import Optional

logger = logging.getLogger(__name__)

# ── Configuration (read once at import time) ─────────────────────────────────

_MODEL_SIZE = os.environ.get("EVA_WHISPER_MODEL", "small")  # small >> base for accuracy
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

    Audio decoding is handled by ffmpeg (not soundfile) to avoid the
    Python 3.14 incompatibility in soundfile's open() call.

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
        self._ffmpeg    = shutil.which("ffmpeg")
        logger.info(
            f"WhisperTranscriber configured: model={model_size}, "
            f"lang={language}, device={device}, ffmpeg={self._ffmpeg}"
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

    def _decode_audio(self, audio_bytes: bytes) -> "numpy.ndarray":
        """
        Use ffmpeg to decode any audio format → mono 16 kHz float32 PCM.

        This bypasses soundfile entirely, avoiding the Python 3.14
        incompatibility where soundfile passes `metadata_errors` to open().
        """
        import numpy as np  # type: ignore

        if not self._ffmpeg:
            raise STTTranscriptionError(
                "ffmpeg is not installed. Install it with: sudo apt install ffmpeg"
            )

        try:
            result = subprocess.run(
                [
                    self._ffmpeg,
                    "-loglevel", "error",
                    "-i",        "pipe:0",    # read from stdin
                    "-ar",       "16000",     # resample to 16 kHz (Whisper native)
                    "-ac",       "1",         # mono
                    # Audio cleanup pipeline:
                    #   highpass=200   – remove low-freq rumble / AC hum
                    #   loudnorm       – normalize loudness (EBU R128)
                    #   aresample      – ensure clean 16 kHz after filtering
                    "-af",       "highpass=f=200,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=16000",
                    "-f",        "f32le",     # raw 32-bit float LE
                    "pipe:1",                # write to stdout
                ],
                input=audio_bytes,
                capture_output=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as exc:
            raise STTTranscriptionError("Audio conversion timed out (>60 s)") from exc

        if result.returncode != 0:
            err = result.stderr.decode(errors="replace").strip()
            raise STTTranscriptionError(f"ffmpeg audio conversion failed: {err}")

        if not result.stdout:
            return np.array([], dtype=np.float32)

        return np.frombuffer(result.stdout, dtype=np.float32)

    # ── Public API ────────────────────────────────────────────────────────────

    def transcribe_bytes(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """
        Transcribe raw audio bytes and return the plain-text transcript.

        Parameters
        ----------
        audio_bytes : bytes
            Raw audio data (WAV, WebM, OGG, MP3 …).
        mime_type : str
            MIME hint (informational; ffmpeg auto-detects the format).

        Returns
        -------
        str
            Transcribed text.  Empty string if nothing was recognised.
        """
        self._load_model()

        # Decode via ffmpeg → numpy float32 array (avoids soundfile / Py 3.14 bug)
        audio_array = self._decode_audio(audio_bytes)

        if len(audio_array) == 0:
            logger.info("Audio contained no samples after decoding — likely silence.")
            return ""

        segments, _info = self._model.transcribe(
            audio_array,
            language=self.language,
            beam_size=5,
            best_of=5,                # consider 5 candidates per beam
            temperature=0.0,          # greedy decoding — most deterministic
            condition_on_previous_text=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        transcript = " ".join(s.text.strip() for s in segments).strip()
        logger.info(f"Transcribed {len(audio_bytes)} bytes → '{transcript[:80]}…'")
        return transcript


# ── Custom exceptions ─────────────────────────────────────────────────────────

class STTDependencyError(RuntimeError):
    """faster-whisper is not installed."""


class STTModelNotAvailableError(RuntimeError):
    """The requested Whisper model has not been downloaded yet."""


class STTTranscriptionError(RuntimeError):
    """Transcription failed for an unexpected reason."""

