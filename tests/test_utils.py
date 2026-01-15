"""
Test utility functions.
"""

import pytest
from utils.summarizer import ContentSummarizer


class TestSummarizerUtils:
    """Test ContentSummarizer utility methods."""

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds only."""
        result = ContentSummarizer._format_duration(45)
        assert result == "45s"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        result = ContentSummarizer._format_duration(125)
        assert result == "2m 5s"

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        result = ContentSummarizer._format_duration(3725)
        assert result == "1h 2m 5s"

    def test_format_duration_zero(self):
        """Test duration formatting for zero."""
        result = ContentSummarizer._format_duration(0)
        assert result == "0s"

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = ContentSummarizer._sanitize_filename("Hello World")
        assert result == "Hello World"

    def test_sanitize_filename_invalid_chars(self):
        """Test removal of invalid filesystem characters."""
        result = ContentSummarizer._sanitize_filename('Test: "File" <name>')
        assert ':' not in result
        assert '"' not in result
        assert '<' not in result
        assert '>' not in result

    def test_sanitize_filename_unicode_quotes(self):
        """Test conversion of Unicode quotes to ASCII."""
        # Test string with Unicode curly quotes: It's a "test"
        test_input = "It\u2019s a \u201ctest\u201d"
        result = ContentSummarizer._sanitize_filename(test_input)
        assert '\u2018' not in result  # No Unicode left single quote
        assert '\u2019' not in result  # No Unicode right single quote
        assert '\u201c' not in result  # No Unicode left double quote
        assert '\u201d' not in result  # No Unicode right double quote

    def test_sanitize_filename_em_dash(self):
        """Test conversion of em dash to regular dash."""
        # Test string with em dash: Test — Name
        test_input = "Test \u2014 Name"
        result = ContentSummarizer._sanitize_filename(test_input)
        assert '\u2014' not in result  # No em dash
        assert '-' in result  # Has regular dash

    def test_sanitize_filename_length_limit(self):
        """Test that filename is limited to 200 characters."""
        long_name = "A" * 300
        result = ContentSummarizer._sanitize_filename(long_name)
        assert len(result) <= 200

    def test_extract_video_id_standard_url(self):
        """Test video ID extraction from standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = ContentSummarizer._extract_video_id(url)
        assert result == "dQw4w9WgXcQ"

    def test_extract_video_id_short_url(self):
        """Test video ID extraction from short YouTube URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = ContentSummarizer._extract_video_id(url)
        assert result == "dQw4w9WgXcQ"

    def test_extract_video_id_with_params(self):
        """Test video ID extraction with extra URL parameters."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
        result = ContentSummarizer._extract_video_id(url)
        assert result == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_url(self):
        """Test video ID extraction from invalid URL."""
        url = "https://example.com/video"
        result = ContentSummarizer._extract_video_id(url)
        assert result == "N/A"

    def test_format_number(self):
        """Test number formatting with commas."""
        assert ContentSummarizer._format_number(1000) == "1,000"
        assert ContentSummarizer._format_number(1234567) == "1,234,567"
        assert ContentSummarizer._format_number(42) == "42"

    def test_format_timestamp_from_seconds(self):
        """Test timestamp formatting from seconds."""
        assert ContentSummarizer._format_timestamp_from_seconds(0) == "00:00:00"
        assert ContentSummarizer._format_timestamp_from_seconds(65) == "00:01:05"
        assert ContentSummarizer._format_timestamp_from_seconds(3661) == "01:01:01"


class TestSummarizerPromptLoading:
    """Test that summarizer can load prompts from prose/."""

    def test_load_system_prompt(self, project_root):
        """Test that system prompt loads without error."""
        import sys
        sys.path.insert(0, str(project_root))

        from utils.summarizer import ContentSummarizer

        # Create a summarizer instance (won't actually call API)
        # Just testing that _load_system_prompt works
        summarizer = ContentSummarizer.__new__(ContentSummarizer)
        summarizer.model = "test"
        summarizer.output_dir = project_root / "summaries"

        # This should not raise an exception
        prompt = summarizer._load_system_prompt()
        assert prompt is not None
        assert len(prompt) > 0
