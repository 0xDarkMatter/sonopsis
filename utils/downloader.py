"""
YouTube Video Downloader Module
Downloads videos from YouTube and extracts audio for transcription.
"""

import os
import yt_dlp
from pathlib import Path
from typing import Dict, Optional


class YouTubeDownloader:
    """Handles downloading YouTube videos and extracting audio."""

    def __init__(self, output_dir: str = "downloads"):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_video(self, url: str, audio_only: bool = True) -> Dict[str, str]:
        """
        Download a YouTube video and extract audio.

        Args:
            url: YouTube video URL
            audio_only: If True, only download audio (default: True)

        Returns:
            Dictionary containing file paths and video metadata

        Raises:
            Exception: If download fails
        """
        # Configure download options
        ydl_opts = {
            'format': 'bestaudio/best' if audio_only else 'best',
            'outtmpl': str(self.output_dir / '%(title).200B.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            'restrictfilenames': True,  # Convert special chars to ASCII
            'windowsfilenames': True,  # Make filenames Windows-safe
        }

        if audio_only:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info
                info = ydl.extract_info(url, download=True)

                # Get the filename
                if audio_only:
                    filename = ydl.prepare_filename(info)
                    # Change extension to mp3
                    audio_file = Path(filename).with_suffix('.mp3')
                else:
                    audio_file = Path(ydl.prepare_filename(info))

                # Sanitize title for safe handling
                title = info.get('title', 'Unknown')
                try:
                    # Try to encode to ensure it's safe
                    title.encode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
                    title = 'Video'

                result = {
                    'title': title,
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0),
                    'audio_file': str(audio_file),
                    'url': url
                }

                return result

        except Exception as e:
            raise Exception(f"Failed to download video: {str(e)}")

    def get_video_info(self, url: str) -> Dict[str, any]:
        """
        Get video information without downloading.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary containing video metadata
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'description': info.get('description', ''),
                }
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")

    def is_playlist(self, url: str) -> bool:
        """
        Check if URL is a playlist.

        Args:
            url: YouTube URL

        Returns:
            True if URL is a playlist, False otherwise
        """
        return 'playlist' in url.lower() or 'list=' in url

    def get_playlist_videos(self, url: str) -> list:
        """
        Extract all video URLs from a playlist.

        Args:
            url: YouTube playlist URL

        Returns:
            List of dictionaries containing video info (url, title, duration)
        """
        print(f"[*] Extracting playlist videos from: {url}")

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download, just get info
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(url, download=False)

                if 'entries' not in playlist_info:
                    raise Exception("No videos found in playlist")

                videos = []
                for entry in playlist_info['entries']:
                    if entry:  # Sometimes entries can be None
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        videos.append({
                            'url': video_url,
                            'title': entry.get('title', 'Unknown'),
                            'duration': entry.get('duration', 0),
                        })

                print(f"[+] Found {len(videos)} videos in playlist")
                return videos

        except Exception as e:
            raise Exception(f"Failed to extract playlist: {str(e)}")
