"""
Test that all modules import correctly.
"""

import pytest


class TestImports:
    """Test module imports."""

    def test_import_sonopsis_package(self):
        """Test that sonopsis package imports."""
        import sonopsis
        assert sonopsis is not None

    def test_import_downloader(self):
        """Test that downloader module imports."""
        from sonopsis import downloader
        assert hasattr(downloader, 'YouTubeDownloader')

    def test_import_transcriber(self):
        """Test that transcriber module imports."""
        from sonopsis import transcriber
        assert hasattr(transcriber, 'AudioTranscriber')

    def test_import_summarizer(self):
        """Test that summarizer module imports."""
        from sonopsis import summarizer
        assert hasattr(summarizer, 'ContentSummarizer')

    def test_downloader_class_exists(self):
        """Test YouTubeDownloader class can be instantiated reference."""
        from sonopsis.downloader import YouTubeDownloader
        assert YouTubeDownloader is not None

    def test_transcriber_class_exists(self):
        """Test AudioTranscriber class can be instantiated reference."""
        from sonopsis.transcriber import AudioTranscriber
        assert AudioTranscriber is not None

    def test_summarizer_class_exists(self):
        """Test ContentSummarizer class can be instantiated reference."""
        from sonopsis.summarizer import ContentSummarizer
        assert ContentSummarizer is not None

    def test_import_tui(self):
        """The interactive interface must at least import - a syntax error
        here would only surface when a user runs `sonopsis tui`."""
        from sonopsis import tui
        assert hasattr(tui, 'main')

    def test_import_cli_entry_point(self):
        from sonopsis.cli import app, run
        assert app is not None and callable(run)


class TestVersionConsistency:
    def test_package_version_matches_pyproject(self):
        """A release tagged from pyproject must match what --version prints."""
        import tomllib
        from pathlib import Path

        import sonopsis

        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            declared = tomllib.load(f)["project"]["version"]
        assert sonopsis.__version__ == declared
