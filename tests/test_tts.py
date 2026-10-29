import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.eva_core.tts.service import SentenceBuffer, TTSService, normalize_speech_text


def test_speech_text_removes_markdown_formatting_without_changing_visible_text():
    text = "**CGPA** is calculated from `grade points`. See [this guide](https://example.com)."
    assert normalize_speech_text(text) == "CGPA is calculated from grade points. See this guide."


def test_speech_text_preserves_natural_apostrophes():
    assert normalize_speech_text("EVA's answer is clear.") == "EVA's answer is clear."


def test_sentence_buffer_preserves_order_and_flushes_remainder():
    buffer = SentenceBuffer()
    assert buffer.add("AI agents can") == []
    assert buffer.add(" perform tasks. Next") == ["AI agents can perform tasks."]
    assert buffer.add(" step!") == ["Next step!"]
    assert buffer.flush() is None


def test_sentence_buffer_flushes_incomplete_text():
    buffer = SentenceBuffer()
    buffer.add("A final chunk")
    assert buffer.flush() == "A final chunk"
    assert buffer.flush() is None


def test_tts_missing_model_is_reported_without_startup_download(monkeypatch, tmp_path):
    monkeypatch.setenv("EVA_TTS_ENABLED", "true")
    monkeypatch.setenv("EVA_TTS_MODEL_PATH", str(tmp_path / "missing.onnx"))
    service = TTSService()
    with pytest.raises(FileNotFoundError, match="en_US-amy-medium"):
        service.initialize()


def test_tts_disabled_does_not_enqueue():
    service = TTSService()
    service.enabled = False
    service.enqueue("Do not speak this")
    assert service.status()["queued"] == 0


def test_tts_speed_maps_to_piper_length_scale(monkeypatch, tmp_path):
    service = TTSService()
    service.speed = 1.5

    class FakeVoice:
        def synthesize_wav(self, text, output, syn_config=None):
            assert text == "Speak quickly."
            assert syn_config.length_scale == pytest.approx(1 / 1.5)

            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(22050)
            output.writeframes(b"\0\0" * 2205)

    service._voice = FakeVoice()
    class FakeProcess:
        def wait(self):
            return 0

        def poll(self):
            return 0

    monkeypatch.setattr("core.eva_core.tts.service.shutil.which", lambda name: "/usr/bin/ffplay")
    monkeypatch.setattr("core.eva_core.tts.service.subprocess.Popen", lambda *args, **kwargs: FakeProcess())
    service._speak("Speak quickly.")


def test_missing_model_failure_is_latched(monkeypatch, tmp_path):
    monkeypatch.setenv("EVA_TTS_MODEL_PATH", str(tmp_path / "missing.onnx"))
    service = TTSService()
    service.initialize = lambda: (_ for _ in ()).throw(FileNotFoundError("missing"))
    service.enqueue("first sentence.")
    service.enqueue("second sentence.")
    service._worker.join(timeout=1)
    assert service._initialization_failed is True
    assert service.status()["queued"] == 0


def test_begin_response_clears_older_audio(monkeypatch):
    service = TTSService()
    service.enabled = True
    service.begin_response("response-1")
    service._queue.put(("old sentence.", "response-1"))
    service.begin_response("response-2")
    assert service.status()["queued"] == 0
    assert service._active_response_id == "response-2"