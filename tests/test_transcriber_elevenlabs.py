"""
Tests for the ElevenLabs transcription path (src/sonopsis/transcriber.py).

The elevenlabs SDK is faked via sys.modules - these tests run without the
elevenlabs extra installed and make no network calls.
"""

import json
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from sonopsis.transcriber import AudioTranscriber


def _t(tmp_path, key="el-key"):
    return AudioTranscriber(output_dir=str(tmp_path), engine="elevenlabs",
                            elevenlabs_api_key=key)


def _audio(tmp_path):
    f = tmp_path / "YT_dQw4w9WgXcQ_talk.mp3"
    f.write_bytes(b"fake-audio")
    return f


def _fake_sdk(response):
    """Build fake elevenlabs modules whose client returns `response`."""
    client = MagicMock()
    client.speech_to_text.convert.return_value = response
    client_mod = types.ModuleType("elevenlabs.client")
    client_mod.ElevenLabs = MagicMock(return_value=client)
    pkg = types.ModuleType("elevenlabs")
    pkg.client = client_mod
    return {"elevenlabs": pkg, "elevenlabs.client": client_mod}, client


def _segmented_response(words, language="en"):
    content = json.dumps({"segments": [{"words": words}]})
    fmt = SimpleNamespace(requested_format="segmented_json", content=content)
    return SimpleNamespace(additional_formats=[fmt], language_code=language,
                           text="plain fallback")


class TestPreflightChecks:
    def test_missing_key_raises(self, tmp_path):
        t = _t(tmp_path, key=None)
        modules, _ = _fake_sdk(SimpleNamespace())
        with patch.dict(sys.modules, modules):
            with pytest.raises(Exception, match="API key"):
                t._transcribe_elevenlabs(_audio(tmp_path), None, False)

    def test_over_ten_hours_raises(self, tmp_path):
        t = _t(tmp_path)
        modules, _ = _fake_sdk(SimpleNamespace())
        with patch.dict(sys.modules, modules), \
             patch.object(AudioTranscriber, "_get_audio_duration",
                          return_value=36001.0):
            with pytest.raises(Exception, match="10 hours"):
                t._transcribe_elevenlabs(_audio(tmp_path), None, False)


class TestDiarizedParsing:
    WORDS = [
        {"text": "Hello", "start": 1.0, "speaker_id": "speaker_0", "type": "word"},
        {"text": " ", "start": 1.2, "speaker_id": "speaker_0", "type": "spacing"},
        {"text": "there", "start": 1.3, "speaker_id": "speaker_0", "type": "word"},
        {"text": "Hi", "start": 2.5, "speaker_id": "speaker_1", "type": "word"},
        {"text": "", "start": 2.6, "speaker_id": "speaker_1", "type": "word"},
    ]

    def _run(self, tmp_path, response):
        t = _t(tmp_path)
        modules, client = _fake_sdk(response)
        with patch.dict(sys.modules, modules), \
             patch.object(AudioTranscriber, "_get_audio_duration",
                          return_value=60.0):
            result = t._transcribe_elevenlabs(_audio(tmp_path), None, False)
        return result, client

    def test_words_grouped_into_speaker_turns(self, tmp_path):
        result, _ = self._run(tmp_path, _segmented_response(self.WORDS))
        assert "**[SPEAKER_0]** `[00:00:01]` Hello there" in result["text"]
        assert "**[SPEAKER_1]** `[00:00:02]` Hi" in result["text"]
        # spacing must not have split speaker_0's turn in two
        assert result["text"].count("SPEAKER_0") == 1

    def test_language_taken_from_response(self, tmp_path):
        result, _ = self._run(tmp_path, _segmented_response(self.WORDS, language="de"))
        assert result["language"] == "de"

    def test_transcript_file_written(self, tmp_path):
        result, _ = self._run(tmp_path, _segmented_response(self.WORDS))
        md = tmp_path / "YT_dQw4w9WgXcQ_talk_transcript.md"
        assert result["text_file"] == str(md)
        assert "ElevenLabs" in md.read_text(encoding="utf-8")

    def test_diarization_requested_with_scribe_v2(self, tmp_path):
        _, client = self._run(tmp_path, _segmented_response(self.WORDS))
        kwargs = client.speech_to_text.convert.call_args.kwargs
        assert kwargs["model_id"] == "scribe_v2"
        assert kwargs["diarize"] is True
        assert "language_code" not in kwargs  # omitted = auto-detect

    def test_no_additional_formats_falls_back_to_plain_text(self, tmp_path):
        response = SimpleNamespace(additional_formats=None, language_code="en",
                                   text="just plain text")
        result, _ = self._run(tmp_path, response)
        assert result["text"] == "just plain text"
