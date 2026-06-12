"""
Tests for transcription engine selection and the openai/parakeet engines.
All network and model access is mocked.
"""

import importlib.util
from unittest.mock import MagicMock, patch

import pytest

from sonopsis.transcriber import AudioTranscriber

HAS_ONNX_ASR = importlib.util.find_spec("onnx_asr") is not None


class TestEngineSelection:
    def test_default_engine_is_whisper_flags(self, tmp_path):
        """Legacy bool flags still resolve correctly (back-compat)."""
        t = AudioTranscriber(output_dir=str(tmp_path), use_elevenlabs=True)
        assert t.engine == "elevenlabs"
        assert t.use_elevenlabs is True

    def test_engine_param_overrides_flags(self, tmp_path):
        t = AudioTranscriber(output_dir=str(tmp_path), use_elevenlabs=True, engine="openai")
        assert t.engine == "openai"
        assert t.use_elevenlabs is False

    def test_openai_engine_constructs_without_model(self, tmp_path):
        t = AudioTranscriber(output_dir=str(tmp_path), engine="openai", openai_api_key="k")
        assert t.model is None

    @pytest.mark.skipif(HAS_ONNX_ASR, reason="onnx-asr installed; missing-extra path untestable")
    def test_parakeet_without_extra_raises_install_hint(self, tmp_path):
        with pytest.raises(ImportError, match="uv sync --extra parakeet"):
            AudioTranscriber(output_dir=str(tmp_path), engine="parakeet")


class TestOpenAIEngine:
    def _transcriber(self, tmp_path):
        return AudioTranscriber(output_dir=str(tmp_path), engine="openai", openai_api_key="test-key")

    def _audio(self, tmp_path):
        f = tmp_path / "YT_dQw4w9WgXcQ_test.mp3"
        f.write_bytes(b"fake-mp3-data")
        return f

    def test_diarized_segments_formatted(self, tmp_path):
        t = self._transcriber(tmp_path)
        audio = self._audio(tmp_path)

        response = MagicMock()
        response.model_dump.return_value = {
            "text": "Hello there. General Kenobi.",
            "segments": [
                {"speaker": "A", "start": 1.0, "end": 3.0, "text": "Hello there."},
                {"speaker": "B", "start": 4.0, "end": 6.0, "text": "General Kenobi."},
            ],
        }
        client = MagicMock()
        client.audio.transcriptions.create.return_value = response

        with patch("openai.OpenAI", return_value=client):
            result = t._transcribe_openai(audio, language=None)

        assert "**[A]** `[00:00:01]` Hello there." in result['text']
        assert "**[B]** `[00:00:04]` General Kenobi." in result['text']

        # diarized_json + auto chunking are required by the API
        kwargs = client.audio.transcriptions.create.call_args.kwargs
        assert kwargs["model"] == "gpt-4o-transcribe-diarize"
        assert kwargs["response_format"] == "diarized_json"
        assert kwargs["chunking_strategy"] == "auto"

        # transcript file written
        files = list(tmp_path.glob("*_transcript.md"))
        assert files and "Hello there." in files[0].read_text(encoding="utf-8")

    def test_plain_text_fallback_when_no_segments(self, tmp_path):
        t = self._transcriber(tmp_path)
        audio = self._audio(tmp_path)

        response = MagicMock()
        response.model_dump.return_value = {"text": "Just plain text.", "segments": []}
        client = MagicMock()
        client.audio.transcriptions.create.return_value = response

        with patch("openai.OpenAI", return_value=client):
            result = t._transcribe_openai(audio, language="en")

        assert result['text'] == "Just plain text."

    def test_empty_transcript_raises(self, tmp_path):
        t = self._transcriber(tmp_path)
        audio = self._audio(tmp_path)

        response = MagicMock()
        response.model_dump.return_value = {"text": "", "segments": []}
        client = MagicMock()
        client.audio.transcriptions.create.return_value = response

        with patch("openai.OpenAI", return_value=client):
            with pytest.raises(Exception, match="empty transcript"):
                t._transcribe_openai(audio, language=None)

    def test_missing_key_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        t = AudioTranscriber(output_dir=str(tmp_path), engine="openai")
        t.openai_api_key = None
        with pytest.raises(Exception, match="API key"):
            t._transcribe_openai(self._audio(tmp_path), language=None)

    def test_small_file_not_reencoded(self, tmp_path):
        t = self._transcriber(tmp_path)
        audio = self._audio(tmp_path)
        assert t._prepare_for_openai(audio) == audio
