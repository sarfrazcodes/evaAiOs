"""Local text-to-speech services for EVA."""

from .service import SentenceBuffer, TTSService, get_tts_service, normalize_speech_text

__all__ = ["SentenceBuffer", "TTSService", "get_tts_service", "normalize_speech_text"]