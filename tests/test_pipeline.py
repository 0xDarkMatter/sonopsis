"""
Tests for the shared pipeline helpers (utils/pipeline.py). No network access.
"""

from utils.pipeline import engine_display_name, find_existing_summary


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
