"""
Tests for the Claude Code CLI summarization backend (claude-cli models).

subprocess and shutil.which are mocked - no real CLI calls are made.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from sonopsis.summarizer import ContentSummarizer, claude_cli_available


FAKE_CLI = r"C:\fake\claude.exe"


def _make_summarizer(tmp_path, model="claude-cli"):
    with patch("sonopsis.summarizer.shutil.which", return_value=FAKE_CLI):
        return ContentSummarizer(model=model, output_dir=str(tmp_path))


class TestClaudeCliDetection:
    def test_available_when_on_path(self):
        with patch("sonopsis.summarizer.shutil.which", return_value=FAKE_CLI):
            assert claude_cli_available() is True

    def test_unavailable_when_missing(self):
        with patch("sonopsis.summarizer.shutil.which", return_value=None):
            assert claude_cli_available() is False


class TestClaudeCliInit:
    def test_init_without_cli_raises(self, tmp_path):
        with patch("sonopsis.summarizer.shutil.which", return_value=None):
            with pytest.raises(ValueError, match="Claude Code CLI not found"):
                ContentSummarizer(model="claude-cli", output_dir=str(tmp_path))

    def test_init_sets_api_type(self, tmp_path):
        s = _make_summarizer(tmp_path)
        assert s.api_type == "claude-cli"
        assert s.cli_path == FAKE_CLI
        assert s.cli_model is None
        assert s.api_key is None

    def test_init_parses_model_alias(self, tmp_path):
        s = _make_summarizer(tmp_path, model="claude-cli/sonnet")
        assert s.cli_model == "sonnet"

    def test_init_needs_no_api_key(self, tmp_path, monkeypatch):
        """claude-cli must work with no API keys in the environment."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        s = _make_summarizer(tmp_path)
        assert s.api_type == "claude-cli"

    def test_plain_claude_model_still_uses_api(self, tmp_path, monkeypatch):
        """Models named claude-* (not claude-cli*) must keep using the Anthropic API."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        s = ContentSummarizer(model="claude-haiku-4-5-20251001", output_dir=str(tmp_path))
        assert s.api_type == "anthropic"


class TestClaudeCliInvocation:
    def _cli_result(self, returncode=0, stdout="", stderr=""):
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_success_returns_summary(self, tmp_path):
        s = _make_summarizer(tmp_path)
        payload = json.dumps({
            "type": "result", "subtype": "success",
            "result": "# Summary\n\nGreat video.", "is_error": False,
        })
        with patch("sonopsis.summarizer.subprocess.run",
                   return_value=self._cli_result(stdout=payload)) as run:
            out = s._summarize_with_claude_cli("system prompt", "user prompt")

        assert out == "# Summary\n\nGreat video."
        cmd = run.call_args[0][0]
        assert cmd[0] == FAKE_CLI
        assert "-p" in cmd
        assert "--output-format" in cmd
        # No --model flag when no alias was given
        assert "--model" not in cmd
        # Transcript travels via stdin, not argv
        assert "user prompt" in run.call_args[1]["input"]
        assert "system prompt" in run.call_args[1]["input"]

    def test_model_alias_passed_through(self, tmp_path):
        s = _make_summarizer(tmp_path, model="claude-cli/haiku")
        payload = json.dumps({"result": "ok", "is_error": False})
        with patch("sonopsis.summarizer.subprocess.run",
                   return_value=self._cli_result(stdout=payload)) as run:
            s._summarize_with_claude_cli("sys", "user")
        cmd = run.call_args[0][0]
        assert cmd[cmd.index("--model") + 1] == "haiku"

    def test_nonzero_exit_raises(self, tmp_path):
        s = _make_summarizer(tmp_path)
        with patch("sonopsis.summarizer.subprocess.run",
                   return_value=self._cli_result(returncode=1, stderr="boom")):
            with pytest.raises(Exception, match="exit 1"):
                s._summarize_with_claude_cli("sys", "user")

    def test_is_error_response_raises(self, tmp_path):
        s = _make_summarizer(tmp_path)
        payload = json.dumps({"result": "rate limited", "is_error": True})
        with patch("sonopsis.summarizer.subprocess.run",
                   return_value=self._cli_result(stdout=payload)):
            with pytest.raises(Exception, match="rate limited"):
                s._summarize_with_claude_cli("sys", "user")

    def test_garbage_output_raises(self, tmp_path):
        s = _make_summarizer(tmp_path)
        with patch("sonopsis.summarizer.subprocess.run",
                   return_value=self._cli_result(stdout="not json")):
            with pytest.raises(Exception, match="unparseable"):
                s._summarize_with_claude_cli("sys", "user")

    def test_empty_summary_raises(self, tmp_path):
        s = _make_summarizer(tmp_path)
        payload = json.dumps({"result": "  ", "is_error": False})
        with patch("sonopsis.summarizer.subprocess.run",
                   return_value=self._cli_result(stdout=payload)):
            with pytest.raises(Exception, match="empty summary"):
                s._summarize_with_claude_cli("sys", "user")
