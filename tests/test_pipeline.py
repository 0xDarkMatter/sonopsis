"""
Tests for the shared pipeline helpers (src/sonopsis/pipeline.py). No network access.
"""

from unittest.mock import patch

from sonopsis.pipeline import engine_display_name, find_existing_summary, process_video


class TestEngineDisplayName:
    def test_whisper_includes_model(self):
        assert engine_display_name("whisper", "small") == "Whisper (small)"

    def test_whisperx_includes_model(self):
        assert engine_display_name("whisperx", "base") == "WhisperX (base)"

    def test_elevenlabs_has_no_model(self):
        assert engine_display_name("elevenlabs") == "ElevenLabs"

    def test_unknown_engine_falls_back(self):
        assert engine_display_name("mystery", "tiny") == "Whisper (tiny)"


class TestFindExistingSummary:
    URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_no_summary(self, tmp_path):
        assert find_existing_summary(self.URL, str(tmp_path)) is None

    def test_existing_summary_found(self, tmp_path):
        summary = tmp_path / "YT_dQw4w9WgXcQ_Some Title_summary.md"
        summary.write_text("# Summary", encoding="utf-8")
        found = find_existing_summary(self.URL, str(tmp_path))
        assert found == summary

    def test_other_videos_dont_match(self, tmp_path):
        (tmp_path / "YT_otherVideo1_Title_summary.md").write_text("x", encoding="utf-8")
        assert find_existing_summary(self.URL, str(tmp_path)) is None

    def test_invalid_url_returns_none(self, tmp_path):
        assert find_existing_summary("https://example.com", str(tmp_path)) is None

    def test_missing_directory_returns_none(self, tmp_path):
        assert find_existing_summary(self.URL, str(tmp_path / "nonexistent")) is None

    def test_multiple_summaries_returns_first_sorted(self, tmp_path):
        """Re-runs with different titles must resolve deterministically."""
        b = tmp_path / "YT_dQw4w9WgXcQ_B Title_summary.md"
        a = tmp_path / "YT_dQw4w9WgXcQ_A Title_summary.md"
        b.write_text("x", encoding="utf-8")
        a.write_text("x", encoding="utf-8")
        assert find_existing_summary(self.URL, str(tmp_path)) == a


class TestProcessVideo:
    """process_video orchestration: cleanup rules, failure shape, and the
    auto-speakers gate. All three stages are mocked - no network or models."""

    URL = "https://youtu.be/dQw4w9WgXcQ"

    def _video_data(self, audio_file, **extra):
        data = {
            "title": "T", "uploader": "U", "duration": 10, "url": self.URL,
            "audio_file": str(audio_file),
        }
        data.update(extra)
        return data

    def _run(self, tmp_path, video_extra=None, **kwargs):
        audio = tmp_path / "YT_dQw4w9WgXcQ_T.mp3"
        audio.write_bytes(b"x")
        video_data = self._video_data(audio, **(video_extra or {}))
        transcript = {"text": "hi", "language": "en", "text_file": "t.md"}
        summary = {"summary": "s", "output_file": "s.md"}

        with patch("sonopsis.pipeline.YouTubeDownloader") as dl, \
             patch("sonopsis.pipeline.AudioTranscriber") as tr, \
             patch("sonopsis.pipeline.ContentSummarizer") as su, \
             patch("sonopsis.pipeline.infer_speaker_count") as infer:
            dl.return_value.download_video.return_value = video_data
            tr.return_value.transcribe.return_value = transcript
            su.return_value.summarize.return_value = summary
            infer.return_value = 3
            result = process_video(self.URL, **kwargs)
        return result, audio, tr, infer

    def test_success_shape_and_cleanup(self, tmp_path):
        result, audio, _, _ = self._run(tmp_path)
        assert result["success"] is True
        assert result["summary_file"] == "s.md"
        assert not audio.exists()  # temp audio cleaned up by default

    def test_keep_files_preserves_audio(self, tmp_path):
        _, audio, _, _ = self._run(tmp_path, keep_files=True)
        assert audio.exists()

    def test_reused_audio_never_deleted(self, tmp_path):
        """An audio file that existed before this run must survive cleanup."""
        _, audio, _, _ = self._run(tmp_path, video_extra={"reused_existing": True})
        assert audio.exists()

    def test_failure_returns_error_dict(self, tmp_path):
        with patch("sonopsis.pipeline.YouTubeDownloader") as dl:
            dl.return_value.download_video.side_effect = Exception("dl boom")
            result = process_video(self.URL)
        assert result == {"success": False, "url": self.URL, "error": "dl boom"}

    def test_auto_speakers_only_for_diarizing_engines(self, tmp_path):
        _, _, tr, infer = self._run(tmp_path, auto_speakers=True,
                                    transcription_engine="parakeet")
        infer.assert_not_called()
        assert tr.call_args.kwargs["num_speakers"] is None

    def test_auto_speakers_inferred_count_passed(self, tmp_path):
        _, _, tr, infer = self._run(tmp_path, auto_speakers=True,
                                    transcription_engine="parakeet-dia")
        infer.assert_called_once()
        assert tr.call_args.kwargs["num_speakers"] == 3

    def test_explicit_num_speakers_wins_over_inference(self, tmp_path):
        _, _, tr, infer = self._run(tmp_path, auto_speakers=True, num_speakers=2,
                                    transcription_engine="parakeet-dia")
        infer.assert_not_called()
        assert tr.call_args.kwargs["num_speakers"] == 2
