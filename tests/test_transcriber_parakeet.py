"""
Tests for the Parakeet transcription path (src/sonopsis/transcriber.py).

The ONNX model and ffmpeg are mocked - what's under test is chunk
orchestration: per-chunk recognition, concatenation, temp cleanup, and the
empty-transcript guard.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sonopsis.transcriber import AudioTranscriber


def _t(tmp_path):
    return AudioTranscriber(output_dir=str(tmp_path), engine="parakeet")


def _chunks(tmp_path, n):
    chunk_dir = tmp_path / "fake_segments"
    chunk_dir.mkdir()
    chunks = []
    for i in range(n):
        c = chunk_dir / f"chunk_{i:04d}.wav"
        c.write_bytes(b"x")
        chunks.append(c)
    return chunks


def _run(tmp_path, recognized, n_chunks=None):
    """Drive _transcribe_parakeet with a fake model returning `recognized`."""
    t = _t(tmp_path)
    audio = tmp_path / "YT_dQw4w9WgXcQ_talk.mp3"
    audio.write_bytes(b"fake")
    chunks = _chunks(tmp_path, n_chunks if n_chunks is not None else len(recognized))

    model = MagicMock()
    model.recognize.side_effect = recognized
    with patch.object(AudioTranscriber, "_ensure_parakeet_model"), \
         patch.object(AudioTranscriber, "_get_audio_duration", return_value=240.0), \
         patch.object(AudioTranscriber, "_segment_to_wav", return_value=chunks):
        t._parakeet_model = model
        result = t._transcribe_parakeet(audio, None)
    return result, chunks, model


class TestParakeetChunking:
    def test_chunks_concatenated_in_order(self, tmp_path):
        result, _, model = _run(tmp_path, ["first part", "second part", "third"])
        assert result["text"] == "first part second part third"
        assert model.recognize.call_count == 3

    def test_empty_chunks_skipped(self, tmp_path):
        """Silent segments (empty recognition) must not inject whitespace."""
        result, _, _ = _run(tmp_path, ["hello", "", "  ", "world"])
        assert result["text"] == "hello world"

    def test_all_empty_raises(self, tmp_path):
        with pytest.raises(Exception, match="empty transcript"):
            _run(tmp_path, ["", "", ""])

    def test_temp_chunks_cleaned_up(self, tmp_path):
        _, chunks, _ = _run(tmp_path, ["a", "b"])
        assert not any(c.exists() for c in chunks)
        assert not chunks[0].parent.exists()

    def test_temp_chunks_cleaned_up_on_failure(self, tmp_path):
        t = _t(tmp_path)
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"x")
        chunks = _chunks(tmp_path, 2)
        model = MagicMock()
        model.recognize.side_effect = RuntimeError("onnx exploded")
        with patch.object(AudioTranscriber, "_ensure_parakeet_model"), \
             patch.object(AudioTranscriber, "_get_audio_duration", return_value=10.0), \
             patch.object(AudioTranscriber, "_segment_to_wav", return_value=chunks):
            t._parakeet_model = model
            with pytest.raises(Exception, match="onnx exploded"):
                t._transcribe_parakeet(audio, None)
        assert not any(c.exists() for c in chunks)

    def test_transcript_file_written(self, tmp_path):
        result, _, _ = _run(tmp_path, ["hello world"])
        md = Path(result["text_file"])
        assert md.exists()
        content = md.read_text(encoding="utf-8")
        assert "NVIDIA Parakeet" in content
        assert "hello world" in content
