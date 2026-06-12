"""
Tests for YouTubeDownloader URL handling (no network access).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

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


class TestBuildMetadata:
    URL = "https://youtu.be/dQw4w9WgXcQ"

    def _build(self, info):
        return YouTubeDownloader._build_metadata(info, Path("a.mp3"), self.URL)

    def test_sparse_info_gets_safe_defaults(self):
        meta = self._build({})
        assert meta["title"] == "Unknown"
        assert meta["duration"] == 0
        assert meta["tags"] == []
        assert meta["reused_existing"] is False
        assert meta["audio_file"] == "a.mp3"
        assert meta["url"] == self.URL

    def test_none_title_falls_back_to_video(self):
        """yt-dlp can return an explicit None title; .encode would raise."""
        meta = self._build({"title": None})
        assert meta["title"] == "Video"

    def test_unencodable_title_falls_back_to_video(self):
        meta = self._build({"title": "bad \ud800 surrogate"})
        assert meta["title"] == "Video"


class TestExistingFileReuse:
    URL = "https://youtu.be/dQw4w9WgXcQ"

    def test_non_tty_auto_reuses_existing_audio(self, tmp_path):
        """Unattended runs (cron, CI) must reuse cached audio, never block."""
        existing = tmp_path / "YT_dQw4w9WgXcQ_Title.mp3"
        existing.write_bytes(b"x")
        dl = YouTubeDownloader(output_dir=str(tmp_path))

        ydl = MagicMock()
        ydl.__enter__ = lambda s: s
        ydl.__exit__ = MagicMock(return_value=False)
        ydl.extract_info.return_value = {"title": "Title"}

        with patch("sonopsis.downloader.sys.stdin") as stdin, \
             patch("sonopsis.downloader.yt_dlp.YoutubeDL", return_value=ydl):
            stdin.isatty.return_value = False
            result = dl.download_video(self.URL)

        assert result["reused_existing"] is True
        assert result["audio_file"] == str(existing)
        ydl.extract_info.assert_called_once_with(self.URL, download=False)

    def test_invalid_url_raises_before_any_download(self, tmp_path):
        dl = YouTubeDownloader(output_dir=str(tmp_path))
        with pytest.raises(Exception, match="Could not extract video ID"):
            dl.download_video("https://example.com/not-youtube")


class TestDownloadVideo:
    URL = "https://youtu.be/dQw4w9WgXcQ"

    def _ydl(self, tmp_path):
        ydl = MagicMock()
        ydl.__enter__ = lambda s: s
        ydl.__exit__ = MagicMock(return_value=False)
        ydl.extract_info.return_value = {"title": "T", "duration": 9}
        ydl.prepare_filename.return_value = str(tmp_path / "YT_dQw4w9WgXcQ_T.webm")
        return ydl

    def test_audio_download_reports_mp3_path(self, tmp_path):
        """audio_only swaps the container extension for the post-processed
        .mp3 - the path handed downstream must match what ffmpeg produced."""
        dl = YouTubeDownloader(output_dir=str(tmp_path))
        ydl = self._ydl(tmp_path)
        with patch("sonopsis.downloader.yt_dlp.YoutubeDL", return_value=ydl):
            result = dl.download_video(self.URL, audio_only=True)
        assert result["audio_file"].endswith(".mp3")
        assert result["reused_existing"] is False
        ydl.extract_info.assert_called_once_with(self.URL, download=True)

    def test_video_download_keeps_original_extension(self, tmp_path):
        dl = YouTubeDownloader(output_dir=str(tmp_path))
        with patch("sonopsis.downloader.yt_dlp.YoutubeDL",
                   return_value=self._ydl(tmp_path)):
            result = dl.download_video(self.URL, audio_only=False)
        assert result["audio_file"].endswith(".webm")

    def test_download_failure_wrapped(self, tmp_path):
        dl = YouTubeDownloader(output_dir=str(tmp_path))
        ydl = self._ydl(tmp_path)
        ydl.extract_info.side_effect = RuntimeError("network down")
        with patch("sonopsis.downloader.yt_dlp.YoutubeDL", return_value=ydl):
            with pytest.raises(Exception, match="Failed to download video: network down"):
                dl.download_video(self.URL)


class TestGetPlaylistVideos:
    URL = "https://www.youtube.com/playlist?list=PLx"

    def _ydl(self, playlist_info):
        ydl = MagicMock()
        ydl.__enter__ = lambda s: s
        ydl.__exit__ = MagicMock(return_value=False)
        ydl.extract_info.return_value = playlist_info
        return ydl

    def test_none_entries_filtered(self, tmp_path):
        """Deleted/private playlist items come back as None - skip them."""
        info = {"entries": [
            {"id": "a" * 11, "title": "A", "duration": 1},
            None,
            {"id": "b" * 11},  # missing title/duration
        ]}
        dl = YouTubeDownloader(output_dir=str(tmp_path))
        with patch("sonopsis.downloader.yt_dlp.YoutubeDL", return_value=self._ydl(info)):
            videos = dl.get_playlist_videos(self.URL)
        assert len(videos) == 2
        assert videos[0]["url"].endswith("a" * 11)
        assert videos[1]["title"] == "Unknown"
        assert videos[1]["duration"] == 0

    def test_missing_entries_key_raises(self, tmp_path):
        dl = YouTubeDownloader(output_dir=str(tmp_path))
        with patch("sonopsis.downloader.yt_dlp.YoutubeDL", return_value=self._ydl({})):
            with pytest.raises(Exception, match="No videos found"):
                dl.get_playlist_videos(self.URL)
