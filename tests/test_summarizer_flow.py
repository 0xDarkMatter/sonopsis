"""
Tests for ContentSummarizer provider selection and the summarize() output
flow (src/sonopsis/summarizer.py). Generation is mocked - no API calls.
"""

from unittest.mock import patch

import pytest

from sonopsis.summarizer import ContentSummarizer


class TestProviderSelection:
    def test_anthropic_missing_key_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            ContentSummarizer(model="claude-sonnet-4-6", output_dir=str(tmp_path))

    def test_openai_missing_key_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            ContentSummarizer(model="gpt-4o-mini", output_dir=str(tmp_path))

    def test_openrouter_missing_key_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            ContentSummarizer(model="openrouter/moonshot/kimi-k2",
                              output_dir=str(tmp_path))

    def test_openrouter_prefix_stripped_for_api(self, tmp_path, monkeypatch):
        """The openrouter/ namespace is ours; the API gets the bare model ID."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        s = ContentSummarizer(model="openrouter/moonshot/kimi-k2",
                              output_dir=str(tmp_path))
        assert s.api_type == "openrouter"
        assert s.model == "moonshot/kimi-k2"

    def test_explicit_api_key_wins_over_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        s = ContentSummarizer(api_key="arg-key", model="gpt-4o-mini",
                              output_dir=str(tmp_path))
        assert s.api_key == "arg-key"

    def test_output_dir_created(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        target = tmp_path / "deep" / "nested"
        ContentSummarizer(model="gpt-4o-mini", output_dir=str(target))
        assert target.is_dir()


class TestSummarizeFlow:
    URL = "https://youtu.be/dQw4w9WgXcQ"

    def _summarizer(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        return ContentSummarizer(model="gpt-4o-mini", output_dir=str(tmp_path))

    def _metadata(self, **extra):
        meta = {"title": "My Video", "uploader": "U", "duration": 60,
                "url": self.URL}
        meta.update(extra)
        return meta

    def _run(self, summarizer, metadata):
        with patch.object(summarizer, "_generate_with_retry",
                          return_value="# Body"):
            return summarizer.summarize("transcript text", metadata)

    def test_output_file_uses_video_id_prefix(self, tmp_path, monkeypatch):
        s = self._summarizer(tmp_path, monkeypatch)
        result = self._run(s, self._metadata())
        assert "YT_dQw4w9WgXcQ_My Video_summary.md" in result["output_file"]
        assert (tmp_path / "YT_dQw4w9WgXcQ_My Video_summary.md").exists()

    def test_no_video_id_falls_back_to_title_only(self, tmp_path, monkeypatch):
        """A non-YouTube URL must not inject 'None' or 'N/A' into the name."""
        s = self._summarizer(tmp_path, monkeypatch)
        result = self._run(s, self._metadata(url="https://example.com/talk"))
        assert (tmp_path / "My Video_summary.md").exists()
        assert "None" not in result["output_file"]

    def test_unsafe_title_sanitised_in_filename(self, tmp_path, monkeypatch):
        s = self._summarizer(tmp_path, monkeypatch)
        result = self._run(s, self._metadata(title='Q&A: "What’s next?" <Part 1/2>'))
        files = list(tmp_path.glob("*_summary.md"))
        assert len(files) == 1
        assert result["output_file"] == str(files[0])

    def test_summary_content_written_to_file(self, tmp_path, monkeypatch):
        s = self._summarizer(tmp_path, monkeypatch)
        result = self._run(s, self._metadata())
        content = (tmp_path / "YT_dQw4w9WgXcQ_My Video_summary.md").read_text(
            encoding="utf-8")
        assert "# Body" in content
        assert result["summary"] == "# Body"

    def test_claude_cli_labelled_correctly_in_output(self, tmp_path):
        """claude-cli summaries must not be attributed to 'OpenAI claude-cli'."""
        with patch("sonopsis.summarizer.shutil.which",
                   return_value=r"C:\fake\claude.exe"):
            s = ContentSummarizer(model="claude-cli", output_dir=str(tmp_path))
        s.transcription_engine = "whisper"
        out = s._format_output("body", self._metadata())
        assert "Claude Code CLI (subscription)" in out
        assert "OpenAI claude-cli" not in out

    def test_claude_cli_alias_shown_in_output(self, tmp_path):
        with patch("sonopsis.summarizer.shutil.which",
                   return_value=r"C:\fake\claude.exe"):
            s = ContentSummarizer(model="claude-cli/haiku", output_dir=str(tmp_path))
        s.transcription_engine = "whisper"
        out = s._format_output("body", self._metadata())
        assert "Claude Code CLI (haiku, subscription)" in out

    def test_generation_error_wrapped(self, tmp_path, monkeypatch):
        s = self._summarizer(tmp_path, monkeypatch)
        with patch.object(s, "_generate_with_retry",
                          side_effect=RuntimeError("api down")):
            with pytest.raises(Exception, match="Summarization failed: api down"):
                s.summarize("text", self._metadata())
        assert list(tmp_path.glob("*_summary.md")) == []  # no partial output
