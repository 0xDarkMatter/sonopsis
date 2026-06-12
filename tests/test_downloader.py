"""
Tests for YouTubeDownloader URL handling (no network access).
"""

import pytest

from sonopsis.downloader import YouTubeDownloader


class TestIsPlaylist:
    def test_playlist_url(self):
        assert YouTubeDownloader.is_playlist(
            "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf") is True

    def test_plain_watch_url(self):
        assert YouTubeDownloader.is_playlist(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ") is False

    def test_watch_url_with_list_param_is_single_video(self):
        """A video opened from within a playlist must process as ONE video."""
        assert YouTubeDownloader.is_playlist(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxyz&index=3") is False

    def test_list_param_without_video_id(self):
        assert YouTubeDownloader.is_playlist(
            "https://www.youtube.com/watch?list=PLxyz") is True

    def test_short_url(self):
        assert YouTubeDownloader.is_playlist("https://youtu.be/dQw4w9WgXcQ") is False

    def test_garbage_url(self):
        assert YouTubeDownloader.is_playlist("not a url at all") is False


class TestExtractVideoId:
    @pytest.mark.parametrize("url,expected", [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=42", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://example.com/video", None),
        ("", None),
    ])
    def test_extract(self, url, expected):
        assert YouTubeDownloader._extract_video_id(url) == expected
