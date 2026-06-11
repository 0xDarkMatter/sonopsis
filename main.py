"""
Sonopsis - YouTube Video Summarizer
Main application entry point (CLI).
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Reconfigure stdout/stderr for UTF-8 on Windows (setting PYTHONIOENCODING
# after interpreter start has no effect on the current process)
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from utils.config import default_engine, load_config
from utils.downloader import YouTubeDownloader
from utils.models import DEFAULT_API_MODEL, DEFAULT_CLI_MODEL
from utils.pipeline import engine_display_name, find_existing_summary, process_video
from utils.summarizer import claude_cli_available


# Initialize colorama for cross-platform colored output
init(autoreset=True)


def print_header():
    """Print application header."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Sonopsis - YouTube Video Summarizer")
    print(f"{Fore.CYAN}{'='*60}\n{Style.RESET_ALL}")


def print_success(message: str):
    """Print success message."""
    print(f"{Fore.GREEN}[+] {message}{Style.RESET_ALL}")


def print_error(message: str):
    """Print error message."""
    print(f"{Fore.RED}[!] {message}{Style.RESET_ALL}")


def print_info(message: str):
    """Print info message."""
    print(f"{Fore.YELLOW}[*] {message}{Style.RESET_ALL}")


def process_playlist(url: str, args, paths: dict):
    """
    Process all videos in a YouTube playlist.

    Args:
        url: YouTube playlist URL
        args: Parsed CLI arguments
        paths: Output directory configuration
    """
    print_header()

    try:
        # Extract playlist videos
        downloader = YouTubeDownloader(output_dir=paths['downloads'])
        videos = downloader.get_playlist_videos(url)

        if not videos:
            print_error("No videos found in playlist")
            sys.exit(1)

        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}Playlist Processing Summary")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        print_info(f"Total videos: {len(videos)}")
        if args.start_from > 1:
            print_info(f"Starting from video: {args.start_from}")
        print_info(f"Transcription: {engine_display_name(args.transcription_engine, args.whisper_model)}")
        print_info(f"AI model: {args.gpt_model}\n")

        # Process each video
        results = []
        successful = 0
        failed = 0
        skipped = 0

        for idx, video in enumerate(videos, 1):
            # Skip videos before start_from
            if idx < args.start_from:
                continue

            # Resumability: skip videos that already have a summary on disk
            if args.skip_existing:
                existing = find_existing_summary(video['url'], paths['summaries'])
                if existing:
                    skipped += 1
                    print_info(f"Skipping video {idx}/{len(videos)} (summary exists: {existing.name})")
                    continue

            try:
                print_info(f"Processing: {video['title']}")
            except UnicodeEncodeError:
                print_info(f"Processing video {idx}/{len(videos)}")

            result = process_video(
                video['url'],
                whisper_model=args.whisper_model,
                gpt_model=args.gpt_model,
                analysis_mode=args.analysis_mode,
                keep_files=args.keep_files,
                transcription_engine=args.transcription_engine,
                num_speakers=args.num_speakers,
                video_num=idx,
                total_videos=len(videos),
                downloads_dir=paths['downloads'],
                transcripts_dir=paths['transcripts'],
                summaries_dir=paths['summaries'],
            )

            results.append(result)

            if result['success']:
                successful += 1
            else:
                failed += 1

            # Running progress update
            print(f"\n{Fore.CYAN}{'─'*60}")
            print(f"{Fore.CYAN}PROGRESS: {successful + failed}/{len(videos) - (args.start_from - 1) - skipped} videos processed")
            print(f"{Fore.CYAN}   Success: {successful}  Failed: {failed}  Skipped: {skipped}")
            print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")

        # Final summary
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}Playlist Processing Complete!")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print_success(f"Successful: {successful}/{len(videos)}")
        if skipped:
            print_info(f"Skipped (already summarized): {skipped}/{len(videos)}")
        if failed > 0:
            print_error(f"Failed: {failed}/{len(videos)}\n")

            print(f"{Fore.RED}Failed videos:{Style.RESET_ALL}")
            for result in results:
                if not result['success']:
                    print(f"  - {result['url']}")
                    print(f"    Error: {result.get('error', 'Unknown')}\n")

    except Exception as e:
        print_error(f"Error processing playlist: {str(e)}")
        sys.exit(1)


def build_parser(config: dict, has_claude_cli: bool) -> argparse.ArgumentParser:
    """Build the CLI argument parser with config-driven defaults."""
    defaults = config['defaults']

    # Prefer the Claude Code CLI (subscription billing) over API models when
    # installed. Precedence: SUMMARY_MODEL env > config.yaml > auto-detect.
    default_summary_model = (
        os.getenv("SUMMARY_MODEL")
        or defaults.get('summary_model')
        or (DEFAULT_CLI_MODEL if has_claude_cli else DEFAULT_API_MODEL)
    )

    parser = argparse.ArgumentParser(
        description="Download, transcribe, and summarize YouTube videos and playlists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single video
  python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
  python main.py https://youtu.be/dQw4w9WgXcQ --whisper-model small

  # Summarize on your Claude subscription (no API key)
  python main.py <URL> --gpt-model claude-cli

  # Playlist (resumable)
  python main.py "https://www.youtube.com/playlist?list=PLxxxxxxx" --skip-existing

  # Keep audio files
  python main.py <URL> --keep-files
        """
    )

    parser.add_argument(
        "url",
        help="YouTube video or playlist URL"
    )

    parser.add_argument(
        "--transcription-engine",
        default=default_engine(defaults.get('transcription_engine')),
        choices=["whisper", "whisperx", "parakeet", "parakeet-dia", "elevenlabs", "openai"],
        help="Transcription engine: whisper (local, free), whisperx (local + speaker diarization), "
             "parakeet (local, beats Whisper accuracy, no PyTorch needed), "
             "elevenlabs (cloud, diarization), openai (cloud gpt-4o-transcribe-diarize) "
             "(default: %(default)s)"
    )

    parser.add_argument(
        "--whisper-model",
        default=os.getenv("WHISPER_MODEL", defaults.get('whisper_model', 'base')),
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size for local transcription (default: %(default)s, not used for elevenlabs)"
    )

    parser.add_argument(
        "--gpt-model",
        default=default_summary_model,
        help=f"AI model for summarization (default: {default_summary_model}). "
             "Use claude-cli[/sonnet|/opus|/haiku] to summarize via the Claude Code CLI "
             "on your Claude subscription instead of an API key."
    )

    parser.add_argument(
        "--analysis-mode",
        default=defaults.get('analysis_mode', 'basic'),
        choices=["basic", "advanced"],
        help="Analysis mode: basic (5 sections) or advanced (9 sections) (default: %(default)s)"
    )

    parser.add_argument(
        "--keep-files",
        action="store_true",
        default=config['processing'].get('keep_files', False),
        help="Keep downloaded audio files"
    )

    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        help="Start processing from video number (for playlists, default: 1)"
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip videos that already have a summary on disk (makes playlist runs resumable)"
    )

    parser.add_argument(
        "--num-speakers",
        type=int,
        default=None,
        help="Known speaker count hint for diarizing engines (parakeet-dia) - "
             "constrains clustering and measurably improves speaker detection"
    )

    return parser


def main():
    """Main entry point."""
    # Load environment variables (.env takes precedence over system env vars)
    load_dotenv(override=True)

    config = load_config()
    paths = config['paths']
    has_claude_cli = claude_cli_available()

    # Parse arguments FIRST so --help and argparse validation work without
    # any API keys configured
    parser = build_parser(config, has_claude_cli)
    args = parser.parse_args()

    # Check for a usable summarization backend: API keys or the Claude Code CLI
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY") \
            and not os.getenv("OPENROUTER_API_KEY") and not has_claude_cli:
        print_error("No summarization backend found.")
        print_info("Either create a .env file with OPENAI_API_KEY or ANTHROPIC_API_KEY,")
        print_info("or install the Claude Code CLI (https://claude.com/claude-code) to use your Claude subscription.")
        print_info("See .env.example for reference.")
        sys.exit(1)

    # Check if URL is a playlist
    if YouTubeDownloader.is_playlist(args.url):
        print_info("Detected: YouTube Playlist\n")
        process_playlist(args.url, args, paths)
    else:
        print_header()
        print_info("Detected: Single Video\n")
        result = process_video(
            args.url,
            whisper_model=args.whisper_model,
            gpt_model=args.gpt_model,
            analysis_mode=args.analysis_mode,
            keep_files=args.keep_files,
            transcription_engine=args.transcription_engine,
            num_speakers=args.num_speakers,
            downloads_dir=paths['downloads'],
            transcripts_dir=paths['transcripts'],
            summaries_dir=paths['summaries'],
        )

        if not result['success']:
            sys.exit(1)


if __name__ == "__main__":
    main()
