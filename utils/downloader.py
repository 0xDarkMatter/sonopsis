"""
YouTube Video Downloader Module
Downloads videos from YouTube and extracts audio for transcription.
"""

import sys
import yt_dlp
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs
from colorama import Fore, Style
import re


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

    def _progress_hook(self, d):
        """Custom progress hook for downloads with cyan progress bar."""
        if d['status'] == 'downloading':
            # Get progress info
            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', 'N/A').strip()
            eta = d.get('_eta_str', 'N/A').strip()

            # Add space above on first call
            if not hasattr(self, '_progress_started'):
                print()
                self._progress_started = True

            # Create progress bar (50 chars wide)
            try:
                percent_float = float(percent.replace('%', ''))
                bar_length = 50
                filled = int(bar_length * percent_float / 100)
                bar = '=' * filled + '-' * (bar_length - filled)

                # Display progress with cyan colors
                progress_text = f"\r{Fore.CYAN}[{bar}] {percent} | {speed} | ETA: {eta}{Style.RESET_ALL}"
                sys.stdout.write(progress_text)
                sys.stdout.flush()
            except Exception:
                # Fallback to simple display
                sys.stdout.write(f"\r{Fore.CYAN}Downloading... {percent}{Style.RESET_ALL}")
                sys.stdout.flush()

        elif d['status'] == 'finished':
            # Clear the line and show completion
            sys.stdout.write(f"\r{Fore.CYAN}{'-' * 80}\n{Style.RESET_ALL}")
            sys.stdout.flush()
            print()  # Space below
            # Reset for next download
            if hasattr(self, '_progress_started'):
                delattr(self, '_progress_started')

    @staticmethod
    def _build_metadata(info: Dict[str, Any], audio_file: Path, url: str) -> Dict[str, Any]:
        """Build the video metadata dict from a yt-dlp info object."""
        # Sanitize title for safe handling
        title = info.get('title', 'Unknown')
        try:
            title.encode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
            title = 'Video'

        return {
            'title': title,
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown'),
            'upload_date': info.get('upload_date', 'Unknown'),
            'description': info.get('description', ''),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'channel_url': info.get('channel_url', ''),
            'tags': info.get('tags', []),
            'categories': info.get('categories', []),
            'chapters': info.get('chapters', []),
            'language': info.get('language', ''),
            'audio_file': str(audio_file),
            'url': url,
            'reused_existing': False,
        }

    def download_video(self, url: str, audio_only: bool = True) -> Dict[str, Any]:
        """
        Download a YouTube video and extract audio.

        Args:
            url: YouTube video URL
            audio_only: If True, only download audio (default: True)

        Returns:
            Dictionary containing file paths and video metadata.
            'reused_existing' is True when a previously downloaded file was
            used instead of downloading - callers should not delete it during
            cleanup.

        Raises:
            Exception: If download fails
        """
        # Extract video ID first
        video_id = self._extract_video_id(url)
        if not video_id:
            raise Exception("Could not extract video ID from URL")

        # Check for existing files. Only prompt on an interactive terminal -
        # unattended runs (cron, CI, piped input) would block forever on
        # input(), so they auto-reuse the cached audio.
        existing_files = list(self.output_dir.glob(f"YT_{video_id}_*.mp3"))
        if existing_files:
            print(f"\n{Fore.YELLOW}[!] Audio file already exists: {existing_files[0].name}{Style.RESET_ALL}")
            # isatty() alone is not enough: on Windows, NUL (subprocess
            # DEVNULL) reports as a tty, so EOF from input() must also count
            # as non-interactive.
            if sys.stdin and sys.stdin.isatty():
                try:
                    response = input(f"{Fore.CYAN}Use downloaded source? (Y/N): {Style.RESET_ALL}").strip().upper()
                    reuse = (response == 'Y')
                except EOFError:
                    print(f"\n{Fore.GREEN}[+] Non-interactive session: reusing existing audio file{Style.RESET_ALL}")
                    reuse = True
            else:
                print(f"{Fore.GREEN}[+] Non-interactive session: reusing existing audio file{Style.RESET_ALL}")
                reuse = True

            if reuse:
                print(f"{Fore.GREEN}[+] Using existing audio file{Style.RESET_ALL}\n")
                result = self._get_metadata_for_existing_file(url, existing_files[0])
                result['reused_existing'] = True
                return result

        # Configure download options with YT_{ID}_{Title} naming
        ydl_opts = {
            'format': 'bestaudio/best' if audio_only else 'best',
            'outtmpl': str(self.output_dir / f'YT_{video_id}_%(title).180B.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,  # A watch URL with &list= should download one video, not the playlist
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            'restrictfilenames': True,  # Convert special chars to ASCII
            'windowsfilenames': True,  # Make filenames Windows-safe
            'progress_hooks': [self._progress_hook],  # Custom progress bar
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

                return self._build_metadata(info, audio_file, url)

        except Exception as e:
            raise Exception(f"Failed to download video: {str(e)}")

    def get_video_info(self, url: str) -> Dict[str, Any]:
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

    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        """
        Extract YouTube video ID from URL.

        Args:
            url: YouTube video URL

        Returns:
            Video ID string (11 characters) or None if not found
        """
        # Handle different YouTube URL formats
        patterns = [
            r'(?:youtube\.com/watch\?(?:[^#]*&)?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/(?:embed|v|shorts|live)/([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _get_metadata_for_existing_file(self, url: str, audio_file: Path) -> Dict[str, Any]:
        """
        Get video metadata without downloading (for existing files).

        Args:
            url: YouTube video URL
            audio_file: Path to existing audio file

        Returns:
            Dictionary containing file paths and video metadata
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return self._build_metadata(info, audio_file, url)

        except Exception as e:
            raise Exception(f"Failed to get video metadata: {str(e)}")

    @staticmethod
    def is_playlist(url: str) -> bool:
        """
        Check if URL refers to a playlist rather than a single video.

        A watch URL that merely carries a `list=` parameter (a video opened
        from within a playlist) counts as a single video - only /playlist
        URLs or `list=` without a video ID are treated as playlists.

        Args:
            url: YouTube URL

        Returns:
            True if URL is a playlist, False otherwise
        """
        try:
            parsed = urlparse(url)
        except ValueError:
            return False

        if '/playlist' in parsed.path.lower():
            return True

        query = parse_qs(parsed.query)
        return 'list' in query and 'v' not in query

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
