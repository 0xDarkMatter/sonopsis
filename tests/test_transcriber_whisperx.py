"""
Tests for the WhisperX fallback contract (src/sonopsis/transcriber.py).

whisperx is not installed in the test environment, so _transcribe_whisperx
hits its ImportError path for real - what's under test is the promised
automatic fallback to vanilla Whisper.
"""

import importlib.util

import pytest
from unittest.mock import patch

from sonopsis.transcriber import AudioTranscriber

HAS_WHISPERX = importlib.util.find_spec("whisperx") is not None

pytestmark = pytest.mark.skipif(
    HAS_WHISPERX, reason="whisperx installed; import-failure path untestable")


def _t(tmp_path):
    return AudioTranscriber(output_dir=str(tmp_path), engine="whisperx")


class TestWhisperXFallback:
    def test_falls_back_to_vanilla_on_failure(self, tmp_path):
        t = _t(tmp_path)
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"x")
        sentinel = {"text": "from vanilla", "language": "en", "text_file": "t.md"}
        with patch.object(AudioTranscriber, "_transcribe_vanilla",
                          return_value=sentinel) as vanilla:
            result = t._transcribe_whisperx(audio, "en", True)
        assert result == sentinel
        # language and podcast_mode must survive the fallback
        assert vanilla.call_args.args[1] == "en"
        assert vanilla.call_args.args[2] is True

    def test_both_engines_failing_reports_both_errors(self, tmp_path):
        t = _t(tmp_path)
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"x")
        with patch.object(AudioTranscriber, "_transcribe_vanilla",
                          side_effect=RuntimeError("vanilla also down")):
            with pytest.raises(Exception, match="Both WhisperX and Whisper failed"):
                t._transcribe_whisperx(audio, None, True)
