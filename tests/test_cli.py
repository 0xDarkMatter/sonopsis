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


class TestHumanOutputContract:
    """Non-JSON mode: rich UI goes to stderr, stdout stays a clean data
    channel (only artifact paths are ever printed there)."""

    @pytest.mark.parametrize("args", [
        ["engines", "list"],
        ["models", "list", "--all"],
        ["auth", "status"],
        ["config", "show"],
    ])
    def test_informational_commands_keep_stdout_clean(self, args):
        result = runner.invoke(app, args)
        assert result.exit_code == 0
        assert result.stdout == ""  # tables/panels render on stderr only

    def test_summarise_prints_only_artifact_path(self):
        process_result = {"success": True, "url": "u", "title": "T",
                          "transcript_file": "t.md", "summary_file": "s.md"}
        with patch("sonopsis.cli._startup"), \
             patch("sonopsis.cli._require_summarization_backend"), \
             patch("sonopsis.pipeline.process_video", return_value=process_result), \
             patch("sonopsis.downloader.YouTubeDownloader.is_playlist", return_value=False):
            result = runner.invoke(app, ["summarise", "https://youtu.be/dQw4w9WgXcQ"])
        assert result.stdout.strip() == "s.md"


class TestEngineStatus:
    def test_exactly_one_default_engine(self):
        from sonopsis.cli import _engine_status
        rows = _engine_status()
        assert sum(1 for r in rows if r["default"]) == 1

    def test_openai_always_installed_needs_key_without_env(self, monkeypatch):
        from sonopsis.cli import _engine_status
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        row = next(r for r in _engine_status() if r["engine"] == "openai")
        assert row["installed"] is True  # SDK ships with the base install
        assert row["needs"] == "OPENAI_API_KEY"

    def test_all_engines_covered(self):
        from sonopsis.cli import _engine_status
        assert {r["engine"] for r in _engine_status()} == set(ENGINES)


class TestTranscribeCommand:
    def test_local_file_not_found_exit_code(self, tmp_path):
        result = runner.invoke(app, ["transcribe", str(tmp_path / "missing.mp3")])
        assert result.exit_code == 3  # EXIT_NOT_FOUND

    def test_local_file_transcribes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        audio = tmp_path / "talk.mp3"
        audio.write_bytes(b"fake")
        fake = {"text": "hello world", "language": "en", "text_file": str(tmp_path / "t.md")}
        with patch("sonopsis.transcriber.AudioTranscriber.__init__", return_value=None), \
             patch("sonopsis.transcriber.AudioTranscriber.transcribe", return_value=fake):
            result = runner.invoke(app, ["transcribe", str(audio), "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.stdout)
        assert envelope["data"]["characters"] == len("hello world")

    def test_pre_existing_local_file_never_deleted(self, tmp_path, monkeypatch):
        """transcribe must not delete a user's own audio file after use."""
        monkeypatch.chdir(tmp_path)
        audio = tmp_path / "keep-me.mp3"
        audio.write_bytes(b"fake")
        fake = {"text": "x", "language": "en", "text_file": "t.md"}
        with patch("sonopsis.transcriber.AudioTranscriber.__init__", return_value=None), \
             patch("sonopsis.transcriber.AudioTranscriber.transcribe", return_value=fake):
            runner.invoke(app, ["transcribe", str(audio)])
        assert audio.exists()

    def test_unknown_engine_validation(self):
        result = runner.invoke(app, ["transcribe", "https://youtu.be/x", "--engine", "bogus"])
        assert result.exit_code == 4

    def test_engine_failure_maps_to_error_exit(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"fake")
        with patch("sonopsis.transcriber.AudioTranscriber.__init__", return_value=None), \
             patch("sonopsis.transcriber.AudioTranscriber.transcribe",
                   side_effect=Exception("engine exploded")):
            result = runner.invoke(app, ["transcribe", str(audio), "--json"])
        assert result.exit_code == 1
        assert json.loads(result.stdout)["error"]["message"] == "engine exploded"


class TestEnginesInstall:
    def test_install_invokes_uv_inexact(self):
        ok = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch("sonopsis.cli.subprocess.run", return_value=ok) as run_mock:
            result = runner.invoke(app, ["engines", "install", "whisper"])
        assert result.exit_code == 0
        cmd = run_mock.call_args.args[0]
        assert cmd[:3] == ["uv", "sync", "--inexact"]
        assert "whisper" in cmd

    def test_install_failure_surfaces_stderr(self):
        bad = type("R", (), {"returncode": 1, "stdout": "", "stderr": "resolver boom"})()
        with patch("sonopsis.cli.subprocess.run", return_value=bad):
            result = runner.invoke(app, ["engines", "install", "whisper", "--json"])
        assert result.exit_code == 1
        assert "resolver boom" in json.loads(result.stdout)["error"]["message"]


class TestJsonErrorEnvelopes:
    def test_validation_error_envelope_shape(self):
        result = runner.invoke(app, ["summarise", "nonsense", "--json"])
        assert result.exit_code == 4
        envelope = json.loads(result.stdout)
        assert envelope["error"]["code"] == "VALIDATION_ERROR"
        assert envelope["error"]["details"]["url"] == "nonsense"


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

    def test_already_verbed_argv_untouched(self):
        """A modern invocation must pass through without double-shimming."""
        assert self._shimmed_argv(["summarise", "https://youtu.be/x"]) == \
            ["summarise", "https://youtu.be/x"]

    def test_url_after_verb_does_not_trigger_summarise(self):
        argv = self._shimmed_argv(["transcribe", "https://youtu.be/x"])
        assert argv[0] == "transcribe"

    def test_flags_only_argv_unchanged(self):
        assert self._shimmed_argv(["--version"]) == ["--version"]

    def test_engine_name_as_value_not_rewritten(self):
        """'whisper' as an option VALUE must not be mistaken for a shortcut flag."""
        argv = self._shimmed_argv(["summarise", "u", "--engine", "whisper"])
        assert argv == ["summarise", "u", "--engine", "whisper"]

    def test_engine_shortcut_works_with_transcribe(self):
        argv = self._shimmed_argv(["transcribe", "u", "--openai"])
        assert argv[-2:] == ["--engine", "openai"]


class TestSummarisePlaylist:
    """Playlist handling: --skip-existing, --start-from, partial failure."""

    URL = "https://www.youtube.com/playlist?list=PLx"

    def _invoke(self, args, videos, process_results, existing_urls=()):
        with patch("sonopsis.cli._startup"), \
             patch("sonopsis.cli._require_summarization_backend"), \
             patch("sonopsis.downloader.YouTubeDownloader.is_playlist", return_value=True), \
             patch("sonopsis.downloader.YouTubeDownloader.get_playlist_videos",
                   return_value=videos), \
             patch("sonopsis.pipeline.find_existing_summary",
                   side_effect=lambda url, d: "s.md" if url in existing_urls else None), \
             patch("sonopsis.pipeline.process_video",
                   side_effect=process_results) as pv:
            result = runner.invoke(app, args)
        return result, pv

    def _videos(self, n):
        return [{"url": f"https://youtu.be/v{i}", "title": f"V{i}"} for i in range(1, n + 1)]

    def _ok(self, url):
        return {"success": True, "url": url, "title": "T",
                "transcript_file": "t.md", "summary_file": "s.md"}

    def test_skip_existing_skips_summarised_videos(self):
        videos = self._videos(3)
        result, pv = self._invoke(
            ["summarise", self.URL, "--skip-existing", "--json"],
            videos,
            process_results=[self._ok(videos[1]["url"])],
            existing_urls=(videos[0]["url"], videos[2]["url"]),
        )
        assert result.exit_code == 0
        envelope = json.loads(result.stdout)
        assert envelope["meta"]["count"] == 3
        assert pv.call_count == 1  # only the un-summarised video processed
        skipped = [row for row in envelope["data"] if row.get("skipped")]
        assert len(skipped) == 2

    def test_start_from_skips_earlier_videos(self):
        videos = self._videos(3)
        result, pv = self._invoke(
            ["summarise", self.URL, "--start-from", "3", "--json"],
            videos,
            process_results=[self._ok(videos[2]["url"])],
        )
        assert result.exit_code == 0
        assert pv.call_count == 1
        assert pv.call_args.args[0] == videos[2]["url"]

    def test_partial_failure_exits_error_with_counts(self):
        videos = self._videos(2)
        result, _ = self._invoke(
            ["summarise", self.URL, "--json"],
            videos,
            process_results=[self._ok(videos[0]["url"]),
                             {"success": False, "url": videos[1]["url"], "error": "boom"}],
        )
        assert result.exit_code == 1
        envelope = json.loads(result.stdout)
        assert envelope["meta"]["succeeded"] == 1
        assert envelope["meta"]["failed"] == 1
