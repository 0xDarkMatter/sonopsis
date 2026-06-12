"""
Tests for the vanilla Whisper transcription path (src/sonopsis/transcriber.py).

The Whisper model is mocked - what's under test is option plumbing (the
anti-hallucination settings), podcast-mode prompting, and output handling.
"""

from unittest.mock import MagicMock, patch

import pytest

from sonopsis.transcriber import AudioTranscriber


def _run(tmp_path, podcast_mode=True, language=None, whisper_result=None):
    t = AudioTranscriber(output_dir=str(tmp_path), engine="whisper")
    audio = tmp_path / "YT_dQw4w9WgXcQ_talk.mp3"
    audio.write_bytes(b"fake")

    model = MagicMock()
    model.transcribe.return_value = whisper_result or {
        "text": "  hello world  ",
        "language": "en",
        "segments": [{"end": 12.0}],
    }
    # duration 0 keeps the progress-bar thread out of the test
    with patch.object(AudioTranscriber, "_ensure_vanilla_model", return_value=model), \
         patch.object(AudioTranscriber, "_get_audio_duration", return_value=0.0):
        result = t._transcribe_vanilla(audio, language, podcast_mode)
    return result, model


class TestVanillaWhisper:
    def test_missing_file_raises_before_model_load(self, tmp_path):
        t = AudioTranscriber(output_dir=str(tmp_path), engine="whisper")
        with pytest.raises(FileNotFoundError):
            t.transcribe(str(tmp_path / "nope.mp3"))

    def test_text_stripped_and_file_written(self, tmp_path):
        result, _ = _run(tmp_path)
        assert result["text"] == "hello world"
        assert result["language"] == "en"
        content = open(result["text_file"], encoding="utf-8").read()
        assert "hello world" in content

    def test_anti_hallucination_options_passed(self, tmp_path):
        """The deterministic/threshold settings are benchmark-backed defaults -
        losing one in a refactor would silently degrade quality."""
        _, model = _run(tmp_path)
        kwargs = model.transcribe.call_args.kwargs
        assert kwargs["temperature"] == 0.0
        assert kwargs["compression_ratio_threshold"] == 2.4
        assert kwargs["logprob_threshold"] == -1.0
        assert kwargs["no_speech_threshold"] == 0.6

    def test_podcast_mode_adds_initial_prompt(self, tmp_path):
        _, model = _run(tmp_path, podcast_mode=True)
        assert "initial_prompt" in model.transcribe.call_args.kwargs

    def test_non_podcast_mode_omits_prompt(self, tmp_path):
        _, model = _run(tmp_path, podcast_mode=False)
        assert "initial_prompt" not in model.transcribe.call_args.kwargs

    def test_language_forwarded(self, tmp_path):
        _, model = _run(tmp_path, language="de")
        assert model.transcribe.call_args.kwargs["language"] == "de"

    def test_empty_segments_safe(self, tmp_path):
        result, _ = _run(tmp_path, whisper_result={
            "text": "short", "language": "en", "segments": []})
        assert result["text"] == "short"

    def test_model_error_wrapped(self, tmp_path):
        t = AudioTranscriber(output_dir=str(tmp_path), engine="whisper")
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"x")
        with patch.object(AudioTranscriber, "_ensure_vanilla_model",
                          side_effect=RuntimeError("cuda oom")):
            with pytest.raises(Exception, match="Transcription failed: cuda oom"):
                t._transcribe_vanilla(audio, None, True)
