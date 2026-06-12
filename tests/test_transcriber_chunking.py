"""
Edge-case tests for long-audio chunking and the OpenAI upload preparation
(src/sonopsis/transcriber.py). ffmpeg/ffprobe calls are mocked.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sonopsis.transcriber import AudioTranscriber


def _t(tmp_path, **kwargs):
    return AudioTranscriber(output_dir=str(tmp_path), engine="openai",
                            openai_api_key="k", **kwargs)


class TestSilenceAlignment:
    def test_short_audio_skips_silence_detection(self, tmp_path):
        """Audio shorter than one chunk must not run silencedetect at all."""
        t = _t(tmp_path, parakeet_chunk_seconds=120)
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"x")
        with patch.object(AudioTranscriber, "_get_audio_duration", return_value=30.0), \
             patch.object(AudioTranscriber, "_detect_silences") as detect, \
             patch("sonopsis.transcriber.subprocess.run") as run_mock:
            run_mock.return_value = MagicMock(returncode=0, stderr="")
            (tmp_path / "ignored").mkdir(exist_ok=True)
            t._segment_to_wav(audio)
        detect.assert_not_called()

    def test_no_silences_falls_back_to_fixed_segments(self, tmp_path):
        """Continuous speech (no detectable silences) must still chunk."""
        t = _t(tmp_path, parakeet_chunk_seconds=10)
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"x")
        with patch.object(AudioTranscriber, "_get_audio_duration", return_value=35.0), \
             patch.object(AudioTranscriber, "_detect_silences", return_value=[]), \
             patch("sonopsis.transcriber.subprocess.run") as run_mock:
            run_mock.return_value = MagicMock(returncode=0, stderr="")
            t._segment_to_wav(audio)
        # fallback path uses ffmpeg -f segment
        cmd = run_mock.call_args.args[0]
        assert "-f" in cmd and "segment" in cmd

    def test_boundaries_snap_to_nearby_silence(self, tmp_path):
        t = _t(tmp_path, parakeet_chunk_seconds=10)
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"x")
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0, stderr="")

        with patch.object(AudioTranscriber, "_get_audio_duration", return_value=20.0), \
             patch.object(AudioTranscriber, "_detect_silences", return_value=[9.0, 17.5]), \
             patch("sonopsis.transcriber.subprocess.run", side_effect=fake_run):
            t._segment_to_wav(audio)
        # per-segment cutting used (not -f segment), first cut at the 9.0s silence
        joined = [" ".join(map(str, c)) for c in calls]
        assert any("-ss 0.000 -to 9.000" in c for c in joined)

    def test_silence_detection_parses_ffmpeg_output(self, tmp_path):
        t = _t(tmp_path)
        stderr = ("[silencedetect @ 0x1] silence_start: 4.5\n"
                  "[silencedetect @ 0x1] silence_end: 5.5 | silence_duration: 1.0\n")
        with patch("sonopsis.transcriber.subprocess.run",
                   return_value=MagicMock(returncode=0, stderr=stderr)):
            mids = t._detect_silences(tmp_path / "a.wav")
        assert mids == [5.0]


class TestOpenAIUploadPrep:
    def test_oversized_file_triggers_reencode(self, tmp_path):
        t = _t(tmp_path)
        audio = tmp_path / "big.mp3"
        audio.write_bytes(b"x" * 10)
        small = audio.with_suffix(".openai.ogg")

        def fake_run(cmd, **kwargs):
            small.write_bytes(b"y" * 5)
            return MagicMock(returncode=0, stderr="")

        with patch.object(Path, "stat") as stat_mock:
            stat_mock.side_effect = lambda *a, **k: MagicMock(
                st_size=30 * 1024 * 1024 if stat_mock.call_count <= 1 else 5)
            with patch("sonopsis.transcriber.subprocess.run", side_effect=fake_run):
                result = t._prepare_for_openai(audio)
        assert result == small

    def test_still_oversized_after_reencode_raises(self, tmp_path):
        t = _t(tmp_path)
        audio = tmp_path / "huge.mp3"
        audio.write_bytes(b"x")
        big = 30 * 1024 * 1024

        def fake_run(cmd, **kwargs):
            audio.with_suffix(".openai.ogg").write_bytes(b"y")
            return MagicMock(returncode=0, stderr="")

        with patch.object(Path, "stat", return_value=MagicMock(st_size=big)), \
             patch("sonopsis.transcriber.subprocess.run", side_effect=fake_run):
            with pytest.raises(Exception, match="exceeds OpenAI's 25MB limit"):
                t._prepare_for_openai(audio)

    def test_reencode_failure_raises_with_stderr(self, tmp_path):
        t = _t(tmp_path)
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"x")
        with patch("sonopsis.transcriber.subprocess.run",
                   return_value=MagicMock(returncode=1, stderr="codec missing")):
            with pytest.raises(Exception, match="codec missing"):
                t._reencode_opus(audio)


class TestDurationProbe:
    """_get_audio_duration must degrade to 0, never raise - it feeds progress
    display and chunk planning, not correctness."""

    def _probe(self, run_result=None, side_effect=None):
        target = "sonopsis.transcriber.subprocess.run"
        patcher = (patch(target, side_effect=side_effect) if side_effect
                   else patch(target, return_value=run_result))
        with patcher:
            return AudioTranscriber._get_audio_duration("a.mp3")

    def test_parses_ffprobe_json(self):
        out = '{"format": {"duration": "123.45"}}'
        assert self._probe(MagicMock(returncode=0, stdout=out)) == 123.45

    def test_ffprobe_failure_returns_zero(self):
        assert self._probe(MagicMock(returncode=1, stdout="")) == 0

    def test_garbage_json_returns_zero(self):
        assert self._probe(MagicMock(returncode=0, stdout="not json")) == 0

    def test_missing_duration_field_returns_zero(self):
        assert self._probe(MagicMock(returncode=0, stdout='{"format": {}}')) == 0

    def test_ffprobe_not_installed_returns_zero(self):
        assert self._probe(side_effect=FileNotFoundError("no ffprobe")) == 0


class TestFormatTimestamp:
    @pytest.mark.parametrize("seconds,expected", [
        (0, "00:00:00"),
        (59.9, "00:00:59"),
        (61, "00:01:01"),
        (3661, "01:01:01"),
        (36000, "10:00:00"),
    ])
    def test_format(self, seconds, expected):
        assert AudioTranscriber._format_timestamp(seconds) == expected
