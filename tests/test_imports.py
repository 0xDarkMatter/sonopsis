"""
Test that all modules import correctly.
"""

import pytest


class TestImports:
    """Test module imports."""

    def test_import_utils_package(self):
        """Test that utils package imports."""
        import utils
        assert utils is not None

    def test_import_downloader(self):
        """Test that downloader module imports."""
        from utils import downloader
        assert hasattr(downloader, 'YouTubeDownloader')

    def test_import_transcriber(self):
        """Test that transcriber module imports."""
        from utils import transcriber
        assert hasattr(transcriber, 'AudioTranscriber')

    def test_import_summarizer(self):
        """Test that summarizer module imports."""
        from utils import summarizer
        assert hasattr(summarizer, 'ContentSummarizer')

    def test_downloader_class_exists(self):
        """Test YouTubeDownloader class can be instantiated reference."""
        from utils.downloader import YouTubeDownloader
        assert YouTubeDownloader is not None

    def test_transcriber_class_exists(self):
        """Test AudioTranscriber class can be instantiated reference."""
        from utils.transcriber import AudioTranscriber
        assert AudioTranscriber is not None

    def test_summarizer_class_exists(self):
        """Test ContentSummarizer class can be instantiated reference."""
        from utils.summarizer import ContentSummarizer
        assert ContentSummarizer is not None
