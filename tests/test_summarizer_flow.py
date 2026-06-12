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


class TestFormatOutputHeader:
    URL = "https://youtu.be/dQw4w9WgXcQ"

    def _formatted(self, tmp_path, monkeypatch, **meta_extra):
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        s = ContentSummarizer(model="gpt-4o-mini", output_dir=str(tmp_path))
        s.transcription_engine = "whisper"
        meta = {"title": "T", "uploader": "U", "duration": 60, "url": self.URL}
        meta.update(meta_extra)
        return s._format_output("THE BODY", meta)

    def test_upload_date_reformatted(self, tmp_path, monkeypatch):
        out = self._formatted(tmp_path, monkeypatch, upload_date="20260115")
        assert "**Published:** 2026-01-15" in out

    def test_unknown_upload_date_left_alone(self, tmp_path, monkeypatch):
        out = self._formatted(tmp_path, monkeypatch)
        assert "**Published:** Unknown" in out

    def test_engagement_section_omitted_when_zero(self, tmp_path, monkeypatch):
        out = self._formatted(tmp_path, monkeypatch, view_count=0, like_count=0)
        assert "Engagement Metrics" not in out

    def test_engagement_counts_formatted_with_commas(self, tmp_path, monkeypatch):
        out = self._formatted(tmp_path, monkeypatch, view_count=1234567)
        assert "**Views:** 1,234,567" in out

    def test_tags_capped_at_twenty(self, tmp_path, monkeypatch):
        out = self._formatted(tmp_path, monkeypatch,
                              tags=[f"t{i}" for i in range(25)])
        assert "(+5 more)" in out
        assert "t19" in out and "t20" not in out

    def test_chapters_listed_with_timestamps(self, tmp_path, monkeypatch):
        out = self._formatted(tmp_path, monkeypatch, chapters=[
            {"start_time": 0, "title": "Intro"},
            {"start_time": 65, "title": "Main"},
        ])
        assert "**Chapters:** 2 detected" in out
        assert "`00:01:05` Main" in out

    def test_summary_body_appended_after_header(self, tmp_path, monkeypatch):
        out = self._formatted(tmp_path, monkeypatch)
        assert out.endswith("THE BODY")
        assert out.index("Processing Information") < out.index("THE BODY")


class TestIdentifySpeakers:
    def _summarizer(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        return ContentSummarizer(model="gpt-4o-mini", output_dir=str(tmp_path))

    def test_no_speaker_labels_returns_empty(self, tmp_path, monkeypatch):
        s = self._summarizer(tmp_path, monkeypatch)
        assert s._identify_speakers("plain transcript, no labels", {}) == ""

    def test_speakers_counted_and_listed(self, tmp_path, monkeypatch):
        s = self._summarizer(tmp_path, monkeypatch)
        transcript = ("**[SPEAKER_0]** `[00:00:01]` Hi\n"
                      "**[SPEAKER_1]** `[00:00:05]` Hello\n"
                      "**[SPEAKER_0]** `[00:00:09]` How are you\n")
        guidance = s._identify_speakers(transcript, {"title": "Chat",
                                                     "uploader": "Show"})
        assert "2 speakers" in guidance
        assert "SPEAKER_0" in guidance and "SPEAKER_1" in guidance
        assert "**Video Title:** Chat" in guidance

    def test_names_extracted_from_description(self, tmp_path, monkeypatch):
        s = self._summarizer(tmp_path, monkeypatch)
        transcript = "**[SPEAKER_0]** hi"
        meta = {"description": "An interview with Jane Doe and John Smith."}
        guidance = s._identify_speakers(transcript, meta)
        assert "Jane Doe" in guidance and "John Smith" in guidance

    def test_only_first_3000_chars_scanned(self, tmp_path, monkeypatch):
        """A speaker appearing only deep into the transcript is outside the
        analysis window - by design, not by accident."""
        s = self._summarizer(tmp_path, monkeypatch)
        transcript = "**[SPEAKER_0]** hi " + "x" * 3000 + " **[SPEAKER_1]** late"
        guidance = s._identify_speakers(transcript, {})
        assert "1 speakers" in guidance


class TestCreateSummaryPrompt:
    URL = "https://youtu.be/dQw4w9WgXcQ"

    def _summarizer(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        return ContentSummarizer(model="gpt-4o-mini", output_dir=str(tmp_path))

    def _metadata(self):
        return {"title": "My Talk", "uploader": "Chan", "duration": 90,
                "url": self.URL}

    @pytest.mark.parametrize("mode", ["basic", "advanced"])
    def test_templates_fill_placeholders(self, tmp_path, monkeypatch, mode):
        s = self._summarizer(tmp_path, monkeypatch)
        prompt = s._create_summary_prompt("UNIQUE-TRANSCRIPT-TOKEN",
                                          self._metadata(), mode)
        assert "UNIQUE-TRANSCRIPT-TOKEN" in prompt
        assert "My Talk" in prompt
        assert "dQw4w9WgXcQ" in prompt
        assert "{title}" not in prompt and "{transcript}" not in prompt

    def test_unknown_mode_raises(self, tmp_path, monkeypatch):
        s = self._summarizer(tmp_path, monkeypatch)
        with pytest.raises(FileNotFoundError, match="analysis_nope"):
            s._create_summary_prompt("t", self._metadata(), "nope")
