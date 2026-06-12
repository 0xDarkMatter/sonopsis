"""
CLI tests for the typer application (src/sonopsis/cli.py).

Uses typer's CliRunner - no subprocesses, no network. Pipeline execution is
mocked; what's under test is the command surface: parsing, validation, exit
codes, JSON envelopes, and the legacy-argv shims.
"""

import json
import sys
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from sonopsis import __version__
from sonopsis.cli import ENGINES, app, run

runner = CliRunner()


class TestBasics:
    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert "summarise" in result.output

    def test_help_lists_subcommands(self):
        result = runner.invoke(app, ["--help"])
        for cmd in ("summarise", "transcribe", "engines", "models", "auth", "config"):
            assert cmd in result.output


class TestSummariseValidation:
    def test_invalid_url_exits_validation(self):
        result = runner.invoke(app, ["summarise", "not-a-url"])
        assert result.exit_code == 4  # EXIT_VALIDATION

    def test_unknown_engine_exits_validation(self):
        result = runner.invoke(app, ["summarise", "https://youtu.be/x", "--engine", "nope"])
        assert result.exit_code == 4

    def test_no_backend_exits_auth_required(self, monkeypatch):
        for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        with patch("sonopsis.cli.claude_cli_available", return_value=False), \
             patch("sonopsis.cli._startup"):
            result = runner.invoke(app, ["summarise", "https://youtu.be/dQw4w9WgXcQ"])
        assert result.exit_code == 2  # EXIT_AUTH_REQUIRED


class TestSummariseExecution:
    def _invoke(self, args, process_result=None):
        process_result = process_result or {
            "success": True, "url": "u", "title": "T",
            "transcript_file": "t.md", "summary_file": "s.md",
        }
        with patch("sonopsis.cli._startup"), \
             patch("sonopsis.cli._require_summarization_backend"), \
             patch("sonopsis.pipeline.process_video", return_value=process_result) as pv, \
             patch("sonopsis.downloader.YouTubeDownloader.is_playlist", return_value=False):
            result = runner.invoke(app, args)
        return result, pv

    def test_summarise_success_prints_summary_path(self):
        result, _ = self._invoke(["summarise", "https://youtu.be/dQw4w9WgXcQ"])
        assert result.exit_code == 0
        assert "s.md" in result.output

    def test_summarise_json_envelope(self):
        result, _ = self._invoke(["summarise", "https://youtu.be/dQw4w9WgXcQ", "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.stdout)
        assert envelope["data"]["summary_file"] == "s.md"
        assert envelope["meta"]["succeeded"] == 1

    def test_summarise_failure_exit_code(self):
        result, _ = self._invoke(
            ["summarise", "https://youtu.be/dQw4w9WgXcQ"],
            process_result={"success": False, "url": "u", "error": "boom"},
        )
        assert result.exit_code == 1

    def test_summarize_alias(self):
        result, _ = self._invoke(["summarize", "https://youtu.be/dQw4w9WgXcQ"])
        assert result.exit_code == 0

    def test_engine_passed_to_pipeline(self):
        _, pv = self._invoke(["summarise", "https://youtu.be/dQw4w9WgXcQ",
                              "--engine", "parakeet"])
        assert pv.call_args.kwargs["transcription_engine"] == "parakeet"


class TestSubapps:
    def test_engines_list_json(self):
        result = runner.invoke(app, ["engines", "list", "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.stdout)
        names = {row["engine"] for row in envelope["data"]}
        assert names == set(ENGINES)

    def test_engines_install_rejects_unknown_pack(self):
        result = runner.invoke(app, ["engines", "install", "nonsense"])
        assert result.exit_code == 4

    def test_models_list_json(self):
        result = runner.invoke(app, ["models", "list", "--all", "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.stdout)
        assert envelope["meta"]["count"] >= 5

    def test_auth_status_json(self):
        result = runner.invoke(app, ["auth", "status", "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.stdout)
        assert "openai" in envelope["data"]
        assert "claude-cli" in envelope["data"]

    def test_auth_login_unknown_provider(self):
        result = runner.invoke(app, ["auth", "login", "nonsense", "--key", "x"])
        assert result.exit_code == 4

    def test_config_show_json(self):
        result = runner.invoke(app, ["config", "show", "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.stdout)
        assert "defaults" in envelope["data"]
        assert "paths" in envelope["data"]


class TestLegacyShims:
    """run() rewrites pre-0.3.0 argv shapes before typer sees them."""

    def _shimmed_argv(self, argv):
        captured = {}
        with patch("sonopsis.cli.app", side_effect=lambda: captured.update(argv=sys.argv[1:])):
            old = sys.argv
            try:
                sys.argv = ["sonopsis"] + argv
                run()
            finally:
                sys.argv = old
        return captured["argv"]

    def test_bare_url_becomes_summarise(self):
        assert self._shimmed_argv(["https://youtu.be/x"])[0] == "summarise"

    def test_engine_shortcut_flag(self):
        argv = self._shimmed_argv(["summarise", "u", "--parakeet"])
        assert argv[-2:] == ["--engine", "parakeet"]

    def test_old_flag_spellings(self):
        argv = self._shimmed_argv(["summarise", "u", "--transcription-engine", "whisper",
                                   "--gpt-model", "claude-cli"])
        assert "--engine" in argv and "--model" in argv
        assert "--transcription-engine" not in argv and "--gpt-model" not in argv
