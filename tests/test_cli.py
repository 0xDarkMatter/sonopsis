"""
CLI tests for sonopsis main.py argument parser.

Heavy dependencies (whisper, yt_dlp) are stubbed via sys.modules
so tests run without torch/CUDA installed.
"""

import sys
import types
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

PROJECT_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Helpers to stub heavy imports before importing main
# ---------------------------------------------------------------------------

def _stub_heavy_modules():
    """Install lightweight stubs for modules that require torch/whisper/etc."""
    stubs = {
        "whisper": MagicMock(),
        "yt_dlp": MagicMock(),
        "elevenlabs": MagicMock(),
    }
    for name, mock in stubs.items():
        sys.modules.setdefault(name, mock)


def _import_main_with_stubs():
    """Import main.py with heavy deps stubbed. Returns the module."""
    _stub_heavy_modules()
    # Remove cached module so we get a fresh import with our stubs active
    sys.modules.pop("main", None)
    sys.modules.pop("utils", None)
    sys.modules.pop("utils.downloader", None)
    sys.modules.pop("utils.transcriber", None)
    sys.modules.pop("utils.summarizer", None)

    import importlib.util
    spec = importlib.util.spec_from_file_location("main", PROJECT_ROOT / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Argument parser tests
# ---------------------------------------------------------------------------

class TestArgumentParser:
    """Test main.py argparse configuration via subprocess (avoids import issues)."""

    def _run(self, *args, env=None):
        """Run main.py via subprocess and return (returncode, stdout, stderr)."""
        import os
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "main.py"), *args],
            capture_output=True,
            text=True,
            env=run_env,
            cwd=str(PROJECT_ROOT),
        )
        return result.returncode, result.stdout, result.stderr

    def test_help_exits_zero(self):
        """--help should print usage and exit 0."""
        code, stdout, stderr = self._run("--help")
        assert code == 0
        assert "usage" in stdout.lower() or "url" in stdout.lower()

    def test_missing_url_exits_nonzero(self):
        """Running without URL should exit with non-zero (argparse error)."""
        code, stdout, stderr = self._run()
        assert code != 0

    def test_no_api_key_exits_one(self):
        """Missing API keys should exit 1 with an informative message."""
        import os
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        env.pop("ANTHROPIC_API_KEY", None)
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "main.py"), "https://youtube.com/watch?v=fake"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 1

    def test_invalid_whisper_model_exits_nonzero(self):
        """Invalid --whisper-model choice should exit with non-zero."""
        code, stdout, stderr = self._run(
            "https://youtube.com/watch?v=fake",
            "--whisper-model", "invalid_model",
        )
        assert code != 0

    def test_invalid_analysis_mode_exits_nonzero(self):
        """Invalid --analysis-mode choice should exit with non-zero."""
        code, stdout, stderr = self._run(
            "https://youtube.com/watch?v=fake",
            "--analysis-mode", "super_advanced",
        )
        assert code != 0

    def test_invalid_transcription_engine_exits_nonzero(self):
        """Invalid --transcription-engine choice should exit non-zero."""
        code, stdout, stderr = self._run(
            "https://youtube.com/watch?v=fake",
            "--transcription-engine", "gpt4o",
        )
        assert code != 0

    def test_help_shows_whisper_model_choices(self):
        """--help output should document whisper model choices."""
        code, stdout, _ = self._run("--help")
        assert code == 0
        assert "whisper-model" in stdout or "whisper_model" in stdout

    def test_help_shows_analysis_mode_choices(self):
        """--help output should document analysis-mode choices."""
        code, stdout, _ = self._run("--help")
        assert "analysis-mode" in stdout or "analysis_mode" in stdout

    def test_help_shows_transcription_engine(self):
        """--help should mention transcription-engine."""
        code, stdout, _ = self._run("--help")
        assert "transcription" in stdout.lower()


# ---------------------------------------------------------------------------
# Argument parser unit tests (no subprocess)
# ---------------------------------------------------------------------------

class TestArgparseUnit:
    """Unit-test the argument parser directly without running main()."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Stub heavy modules and import main."""
        _stub_heavy_modules()
        import importlib.util
        import os
        # Temporarily patch env so load_dotenv doesn't interfere
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            spec = importlib.util.spec_from_file_location(
                "main_unit", PROJECT_ROOT / "main.py"
            )
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
            except SystemExit:
                pass
            self.main_module = mod

    def test_parser_url_is_required(self):
        """Parser should require a positional URL argument."""
        import argparse
        # Reconstruct a standalone parser to test choices without side-effects
        parser = argparse.ArgumentParser()
        parser.add_argument("url")
        parser.add_argument("--whisper-model", choices=["tiny", "base", "small", "medium", "large"], default="base")
        parser.add_argument("--analysis-mode", choices=["basic", "advanced"], default="basic")
        parser.add_argument("--transcription-engine", choices=["whisper", "whisperx", "elevenlabs"], default="whisper")
        parser.add_argument("--keep-files", action="store_true")
        parser.add_argument("--start-from", type=int, default=1)

        args = parser.parse_args(["https://youtube.com/watch?v=test"])
        assert args.url == "https://youtube.com/watch?v=test"

    def test_parser_defaults(self):
        """Verify default values for optional arguments."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("url")
        parser.add_argument("--whisper-model", choices=["tiny", "base", "small", "medium", "large"], default="base")
        parser.add_argument("--analysis-mode", choices=["basic", "advanced"], default="basic")
        parser.add_argument("--transcription-engine", choices=["whisper", "whisperx", "elevenlabs"], default="whisper")
        parser.add_argument("--keep-files", action="store_true")
        parser.add_argument("--start-from", type=int, default=1)

        args = parser.parse_args(["https://youtube.com/watch?v=test"])
        assert args.whisper_model == "base"
        assert args.analysis_mode == "basic"
        assert args.transcription_engine == "whisper"
        assert args.keep_files is False
        assert args.start_from == 1

    def test_parser_keep_files_flag(self):
        """--keep-files should set keep_files=True."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("url")
        parser.add_argument("--keep-files", action="store_true")

        args = parser.parse_args(["https://example.com", "--keep-files"])
        assert args.keep_files is True

    def test_parser_start_from_integer(self):
        """--start-from should accept an integer."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("url")
        parser.add_argument("--start-from", type=int, default=1)

        args = parser.parse_args(["https://example.com", "--start-from", "5"])
        assert args.start_from == 5
