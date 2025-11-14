"""
Sonopsis - YouTube Video Summarizer
Main application entry point.
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from utils.downloader import YouTubeDownloader
from utils.transcriber import AudioTranscriber
from utils.summarizer import ContentSummarizer


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


def process_single_video(url: str, whisper_model: str = "base", gpt_model: str = "gpt-4o-mini",
                         analysis_mode: str = "basic", keep_files: bool = False,
                         transcription_engine: str = "whisper",
                         video_num: int = None, total_videos: int = None):
    """
    Process a single YouTube video: download, transcribe, and summarize.

    Args:
        url: YouTube video URL
        whisper_model: Whisper model size (tiny, base, small, medium, large)
        gpt_model: GPT model for summarization
        analysis_mode: Analysis mode (basic or advanced)
        keep_files: Whether to keep downloaded audio files
        transcription_engine: Transcription engine (whisper, whisperx, or elevenlabs)
        video_num: Current video number (for batch processing)
        total_videos: Total number of videos (for batch processing)

    Returns:
        Dictionary with success status and results
    """
    if video_num and total_videos:
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA}Processing Video {video_num}/{total_videos}")
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")

    try:
        # Step 1: Download video
        print_info("Step 1/3: Downloading video...")
        downloader = YouTubeDownloader(output_dir="downloads")
        video_data = downloader.download_video(url, audio_only=True)
        print_success(f"Downloaded: {video_data['title']}")

        # Step 2: Transcribe audio
        engine_names = {
            "whisper": "Whisper",
            "whisperx": "WhisperX",
            "elevenlabs": "ElevenLabs"
        }
        engine_display = engine_names.get(transcription_engine, "Whisper")
        model_info = f" ({whisper_model})" if transcription_engine != "elevenlabs" else ""

        print_info(f"\nStep 2/3: Transcribing audio with {engine_display}{model_info}...")
        transcriber = AudioTranscriber(
            model_name=whisper_model,
            output_dir="transcripts",
            use_whisperx=(transcription_engine == "whisperx"),
            hf_token=os.getenv("HF_TOKEN"),
            use_elevenlabs=(transcription_engine == "elevenlabs"),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY")
        )
        transcript_data = transcriber.transcribe(video_data['audio_file'])
        print_success(f"Transcription complete ({transcript_data['language']})")

        # Step 3: Generate summary
        print_info("\nStep 3/3: Generating summary...")
        summarizer = ContentSummarizer(model=gpt_model, output_dir="summaries")

        # Combine video metadata for summary
        metadata = {
            'title': video_data['title'],
            'uploader': video_data['uploader'],
            'duration': video_data['duration'],
            'url': video_data['url'],
            'whisper_model': whisper_model
        }

        summary_data = summarizer.summarize(
            transcript_data['text'],
            metadata,
            analysis_mode,
            transcription_engine=transcription_engine
        )
        print_success("Summary generated")

        # Cleanup
        if not keep_files:
            print_info("\nCleaning up temporary files...")
            audio_file = Path(video_data['audio_file'])
            if audio_file.exists():
                audio_file.unlink()
                print_success(f"Removed: {audio_file.name}")

        # Print results
        print(f"\n{Fore.GREEN}{'='*60}")
        if video_num and total_videos:
            print(f"{Fore.GREEN}✓ Video {video_num}/{total_videos} Complete! ({total_videos - video_num} remaining){Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Processing Complete!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*60}\n")

        print(f"{Fore.WHITE}Video: {Fore.YELLOW}{video_data['title']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Transcript: {Fore.YELLOW}{transcript_data['text_file']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Summary: {Fore.YELLOW}{summary_data['output_file']}{Style.RESET_ALL}\n")

        return {
            'success': True,
            'video': video_data,
            'transcript': transcript_data,
            'summary': summary_data
        }

    except Exception as e:
        print_error(f"Error: {str(e)}\n")
        return {
            'success': False,
            'url': url,
            'error': str(e)
        }


def process_playlist(url: str, whisper_model: str = "base", gpt_model: str = "gpt-4o-mini",
                     analysis_mode: str = "basic", keep_files: bool = False,
                     transcription_engine: str = "whisper", start_from: int = 1):
    """
    Process all videos in a YouTube playlist.

    Args:
        url: YouTube playlist URL
        whisper_model: Whisper model size
        gpt_model: GPT model for summarization
        analysis_mode: Analysis mode (basic or advanced)
        keep_files: Whether to keep downloaded audio files
        transcription_engine: Transcription engine (whisper, whisperx, or elevenlabs)
        start_from: Video number to start from (1-indexed)
    """
    print_header()

    try:
        # Extract playlist videos
        downloader = YouTubeDownloader(output_dir="downloads")
        videos = downloader.get_playlist_videos(url)

        if not videos:
            print_error("No videos found in playlist")
            sys.exit(1)

        engine_names = {
            "whisper": "Whisper",
            "whisperx": "WhisperX",
            "elevenlabs": "ElevenLabs"
        }
        engine_display = engine_names.get(transcription_engine, "Whisper")
        model_info = f" ({whisper_model})" if transcription_engine != "elevenlabs" else ""

        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}Playlist Processing Summary")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        print_info(f"Total videos: {len(videos)}")
        if start_from > 1:
            print_info(f"Starting from video: {start_from}")
        print_info(f"Transcription: {engine_display}{model_info}")
        print_info(f"AI model: {gpt_model}\n")

        # Process each video
        results = []
        successful = 0
        failed = 0

        for idx, video in enumerate(videos, 1):
            # Skip videos before start_from
            if idx < start_from:
                continue
            try:
                print_info(f"Processing: {video['title']}")
            except UnicodeEncodeError:
                print_info(f"Processing video {idx}/{len(videos)}")

            result = process_single_video(
                video['url'],
                whisper_model,
                gpt_model,
                analysis_mode,
                keep_files,
                transcription_engine,
                video_num=idx,
                total_videos=len(videos)
            )

            results.append(result)

            if result['success']:
                successful += 1
                # Print running progress update
                videos_processed = successful + failed
                videos_to_process = len(videos) - (start_from - 1)
                print(f"\n{Fore.CYAN}{'─'*60}")
                print(f"{Fore.CYAN}📊 PROGRESS: {videos_processed}/{videos_to_process} videos processed")
                print(f"{Fore.CYAN}   ✓ Success: {successful}  ✗ Failed: {failed}")
                print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")
            else:
                failed += 1

        # Final summary
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}Playlist Processing Complete!")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print_success(f"Successful: {successful}/{len(videos)}")
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


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()

    # Check for API keys
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print_error("No API keys found in environment variables.")
        print_info("Please create a .env file with OPENAI_API_KEY or ANTHROPIC_API_KEY.")
        print_info("See .env.example for reference.")
        sys.exit(1)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Download, transcribe, and summarize YouTube videos and playlists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single video
  python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
  python main.py https://youtu.be/dQw4w9WgXcQ --whisper-model small

  # Playlist
  python main.py "https://www.youtube.com/playlist?list=PLxxxxxxx"
  python main.py <PLAYLIST_URL> --gpt-model claude-sonnet-4-5-20250929

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
        default="whisper",
        choices=["whisper", "whisperx", "elevenlabs"],
        help="Transcription engine: whisper (local, free), whisperx (local with speaker diarization), elevenlabs (cloud, paid) (default: whisper)"
    )

    parser.add_argument(
        "--whisper-model",
        default=os.getenv("WHISPER_MODEL", "base"),
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size for local transcription (default: base, not used for elevenlabs)"
    )

    parser.add_argument(
        "--gpt-model",
        default=os.getenv("SUMMARY_MODEL", "claude-sonnet-4-5-20250929"),
        help="AI model for summarization (default: claude-sonnet-4-5-20250929)"
    )

    parser.add_argument(
        "--analysis-mode",
        default="basic",
        choices=["basic", "advanced"],
        help="Analysis mode: basic (5 sections) or advanced (9 sections) (default: basic)"
    )

    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep downloaded audio files"
    )

    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        help="Start processing from video number (for playlists, default: 1)"
    )

    args = parser.parse_args()

    # Check if URL is a playlist
    downloader = YouTubeDownloader(output_dir="downloads")
    is_playlist = downloader.is_playlist(args.url)

    if is_playlist:
        print_info("Detected: YouTube Playlist\n")
        process_playlist(
            url=args.url,
            whisper_model=args.whisper_model,
            gpt_model=args.gpt_model,
            analysis_mode=args.analysis_mode,
            keep_files=args.keep_files,
            transcription_engine=args.transcription_engine,
            start_from=args.start_from
        )
    else:
        print_header()
        print_info("Detected: Single Video\n")
        result = process_single_video(
            url=args.url,
            whisper_model=args.whisper_model,
            gpt_model=args.gpt_model,
            analysis_mode=args.analysis_mode,
            keep_files=args.keep_files,
            transcription_engine=args.transcription_engine
        )

        if not result['success']:
            sys.exit(1)


if __name__ == "__main__":
    main()
