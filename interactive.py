"""
Sonopsis - Interactive YouTube Video Summarizer
User-friendly interface with model selection menus.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

from utils.downloader import YouTubeDownloader
from utils.transcriber import AudioTranscriber
from utils.summarizer import ContentSummarizer

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()


def print_header():
    """Print application header."""
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}      Sonopsis - Interactive Mode")
    print(f"{Fore.CYAN}{'='*70}\n{Style.RESET_ALL}")


def print_section_header(title):
    """Print a section header."""
    print(f"\n{Fore.YELLOW}{'-'*70}")
    print(f"{Fore.YELLOW}{title}")
    print(f"{Fore.YELLOW}{'-'*70}{Style.RESET_ALL}\n")


def get_youtube_url():
    """Get YouTube URL from user."""
    print_section_header("Step 1: YouTube Video/Playlist URL")

    while True:
        url = input(f"{Fore.WHITE}Enter YouTube URL or Playlist URL (or 'q' to quit): {Style.RESET_ALL}").strip()

        if url.lower() == 'q':
            print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
            sys.exit(0)

        if 'youtube.com' in url or 'youtu.be' in url:
            return url

        print(f"{Fore.RED}[!] Invalid URL. Please enter a valid YouTube URL.{Style.RESET_ALL}\n")


def select_whisper_model():
    """Interactive Whisper model selection."""
    print_section_header("Step 2: Select Whisper Transcription Model")

    models = {
        '1': {
            'name': 'tiny',
            'size': '~75 MB',
            'speed': 'Fastest',
            'quality': 'Good',
            'desc': 'Multilingual speech recognition, good for podcasts and interviews',
            'icon': '[FAST]',
            'color': Fore.YELLOW
        },
        '2': {
            'name': 'base',
            'size': '~150 MB',
            'speed': 'Fast',
            'quality': 'Better',
            'desc': 'Balanced accuracy and speed, handles most accents well',
            'icon': '[RECOMMENDED]',
            'color': Fore.GREEN
        },
        '3': {
            'name': 'small',
            'size': '~500 MB',
            'speed': 'Medium',
            'quality': 'Great',
            'desc': 'Better for technical content, reduces word errors significantly',
            'icon': '[QUALITY]',
            'color': Fore.CYAN
        },
        '4': {
            'name': 'medium',
            'size': '~1.5 GB',
            'speed': 'Slow',
            'quality': 'Excellent',
            'desc': 'Professional quality, excellent for medical/legal transcriptions',
            'icon': '[PRO]',
            'color': Fore.MAGENTA
        },
        '5': {
            'name': 'large',
            'size': '~3 GB',
            'speed': 'Slowest',
            'quality': 'Best',
            'desc': 'Maximum accuracy, handles difficult audio and heavy accents',
            'icon': '[MAX]',
            'color': Fore.RED
        },
    }

    print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  WHISPER TRANSCRIPTION MODELS{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

    for key, info in models.items():
        # Model name line with icon
        icon_colored = f"{info['color']}{info['icon']}{Style.RESET_ALL}"
        print(f"{Fore.GREEN}[{key}]{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}{info['name'].upper():<8}{Style.RESET_ALL} {icon_colored}")

        # Stats line
        print(f"    {Fore.CYAN}Size:{Style.RESET_ALL} {info['size']:<10} "
              f"{Fore.CYAN}Speed:{Style.RESET_ALL} {info['speed']:<8} "
              f"{Fore.CYAN}Quality:{Style.RESET_ALL} {info['quality']}")

        # Description
        print(f"    {Fore.WHITE}{info['desc']}{Style.RESET_ALL}\n")

    # Check cache for already downloaded models
    cache_dir = Path(os.getenv("WHISPER_CACHE_DIR", "E:/Coding/WhisperCache"))
    if cache_dir.exists():
        downloaded = [f.stem for f in cache_dir.glob('*.pt')]
        if downloaded:
            print(f"{Fore.GREEN}[CACHE]{Style.RESET_ALL} Already downloaded: {Fore.YELLOW}{', '.join(downloaded)}{Style.RESET_ALL}")
            print(f"        Location: {Fore.CYAN}{cache_dir}{Style.RESET_ALL}\n")

    while True:
        choice = input(f"\n{Fore.WHITE}Select model (1-5) [default: 2 - base]: {Style.RESET_ALL}").strip()

        if not choice:
            choice = '2'

        if choice in models:
            selected = models[choice]
            print(f"{Fore.GREEN}[+] Selected: {selected['name']} model{Style.RESET_ALL}")
            return selected['name']

        print(f"{Fore.RED}[!] Invalid choice. Please enter 1-5.{Style.RESET_ALL}")


def select_summary_model():
    """Interactive AI model selection for summarization."""
    print_section_header("Step 3: Select AI Summarization Model")

    # Check which API keys are available
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    models = {}
    model_num = 1

    if has_openai:
        print(f"\n{Fore.YELLOW}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  OPENAI MODELS{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}\n")

        # GPT-4o-mini
        models[str(model_num)] = {'name': 'gpt-4o-mini', 'provider': 'OpenAI',
                                   'cost': '$0.05', 'speed': 'Fastest', 'quality': 'Good',
                                   'desc': 'Budget-friendly, great for simple summaries and quick overviews'}
        print(f"{Fore.GREEN}[{model_num}]{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}GPT-4O-MINI{Style.RESET_ALL} "
              f"{Fore.GREEN}[BUDGET]{Style.RESET_ALL}")
        print(f"    {Fore.CYAN}Speed:{Style.RESET_ALL} Fastest    {Fore.CYAN}Cost:{Style.RESET_ALL} ~$0.05    {Fore.CYAN}Quality:{Style.RESET_ALL} Good")
        print(f"    {Fore.WHITE}{models[str(model_num)]['desc']}{Style.RESET_ALL}\n")
        model_num += 1

        # GPT-4o
        models[str(model_num)] = {'name': 'gpt-4o', 'provider': 'OpenAI',
                                   'cost': '$0.15', 'speed': 'Fast', 'quality': 'Great',
                                   'desc': 'Balanced model, good analysis and structured summaries'}
        print(f"{Fore.GREEN}[{model_num}]{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}GPT-4O{Style.RESET_ALL} "
              f"{Fore.CYAN}[BALANCED]{Style.RESET_ALL}")
        print(f"    {Fore.CYAN}Speed:{Style.RESET_ALL} Fast       {Fore.CYAN}Cost:{Style.RESET_ALL} ~$0.15    {Fore.CYAN}Quality:{Style.RESET_ALL} Great")
        print(f"    {Fore.WHITE}{models[str(model_num)]['desc']}{Style.RESET_ALL}\n")
        model_num += 1

        # GPT-5
        models[str(model_num)] = {'name': 'gpt-5', 'provider': 'OpenAI',
                                   'cost': '$0.30', 'speed': 'Slow', 'quality': 'Excellent',
                                   'desc': 'PhD-level reasoning, catches transcript errors, most accurate'}
        print(f"{Fore.GREEN}[{model_num}]{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}GPT-5{Style.RESET_ALL} "
              f"{Fore.MAGENTA}[PHD-LEVEL]{Style.RESET_ALL}")
        print(f"    {Fore.CYAN}Speed:{Style.RESET_ALL} Slow       {Fore.CYAN}Cost:{Style.RESET_ALL} ~$0.30    {Fore.CYAN}Quality:{Style.RESET_ALL} Excellent")
        print(f"    {Fore.WHITE}{models[str(model_num)]['desc']}{Style.RESET_ALL}\n")
        model_num += 1

    if has_anthropic:
        print(f"{Fore.MAGENTA}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}  ANTHROPIC CLAUDE MODELS{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*70}{Style.RESET_ALL}\n")

        # Claude Haiku 4.5
        models[str(model_num)] = {'name': 'claude-haiku-4-5-20251001', 'provider': 'Anthropic',
                                   'cost': '$0.08', 'speed': 'Very Fast', 'quality': 'Excellent',
                                   'desc': 'Best value: 90% of Sonnet quality at 1/3 cost, very fast'}
        print(f"{Fore.GREEN}[{model_num}]{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}CLAUDE HAIKU 4.5{Style.RESET_ALL} "
              f"{Fore.YELLOW}[BEST VALUE]{Style.RESET_ALL}")
        print(f"    {Fore.CYAN}Speed:{Style.RESET_ALL} Very Fast  {Fore.CYAN}Cost:{Style.RESET_ALL} ~$0.08    {Fore.CYAN}Quality:{Style.RESET_ALL} Excellent")
        print(f"    {Fore.WHITE}{models[str(model_num)]['desc']}{Style.RESET_ALL}\n")
        model_num += 1

        # Claude Sonnet 4.5
        models[str(model_num)] = {'name': 'claude-sonnet-4-5-20250929', 'provider': 'Anthropic',
                                   'cost': '$0.25', 'speed': 'Medium', 'quality': 'Best',
                                   'desc': 'Top quality: best overall analysis, detailed insights, world-class'}
        print(f"{Fore.GREEN}[{model_num}]{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}CLAUDE SONNET 4.5{Style.RESET_ALL} "
              f"{Fore.RED}[TOP QUALITY]{Style.RESET_ALL}")
        print(f"    {Fore.CYAN}Speed:{Style.RESET_ALL} Medium     {Fore.CYAN}Cost:{Style.RESET_ALL} ~$0.25    {Fore.CYAN}Quality:{Style.RESET_ALL} Best")
        print(f"    {Fore.WHITE}{models[str(model_num)]['desc']}{Style.RESET_ALL}\n")
        model_num += 1

    if not has_openai and not has_anthropic:
        print(f"{Fore.RED}[!] No API keys found in .env file!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[*] Please add OPENAI_API_KEY or ANTHROPIC_API_KEY to your .env file{Style.RESET_ALL}")
        sys.exit(1)

    print(f"{Fore.YELLOW}{'─'*70}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Note:{Style.RESET_ALL} Costs shown are approximate for a 3-hour video")
    print(f"{Fore.YELLOW}{'─'*70}{Style.RESET_ALL}")

    while True:
        choice = input(f"\n{Fore.WHITE}Select model (1-{len(models)}) [default: Claude Haiku if available, else gpt-4o-mini]: {Style.RESET_ALL}").strip()

        if not choice:
            # Default to Claude Haiku if available, else gpt-4o-mini
            if has_anthropic:
                for k, v in models.items():
                    if 'haiku' in v['name']:
                        choice = k
                        break
            else:
                choice = '1'

        if choice in models:
            selected = models[choice]
            print(f"{Fore.GREEN}[+] Selected: {selected['name']}{Style.RESET_ALL}")
            return selected['name']

        print(f"{Fore.RED}[!] Invalid choice. Please enter 1-{len(models)}.{Style.RESET_ALL}")


def process_single_video(url, whisper_model, summary_model, keep_files, video_num=None, total_videos=None):
    """Process a single video with selected models."""

    # Add video counter to header if processing multiple videos
    if video_num and total_videos:
        print(f"\n{Fore.MAGENTA}{'='*70}")
        print(f"{Fore.MAGENTA}  Processing Video {video_num}/{total_videos}")
        print(f"{Fore.MAGENTA}{'='*70}{Style.RESET_ALL}\n")

    try:
        # Step 1: Download
        print(f"{Fore.CYAN}[1/3] Downloading video...{Style.RESET_ALL}")
        downloader = YouTubeDownloader(output_dir="downloads")
        video_data = downloader.download_video(url, audio_only=True)
        print(f"{Fore.GREEN}[+] Download complete{Style.RESET_ALL}\n")

        # Step 2: Transcribe
        print(f"{Fore.CYAN}[2/3] Transcribing audio with {whisper_model} model...{Style.RESET_ALL}")
        transcriber = AudioTranscriber(model_name=whisper_model, output_dir="transcripts")
        transcript_data = transcriber.transcribe(video_data['audio_file'])
        print(f"{Fore.GREEN}[+] Transcription complete ({transcript_data['language']}){Style.RESET_ALL}\n")

        # Step 3: Summarize
        print(f"{Fore.CYAN}[3/3] Generating summary with {summary_model}...{Style.RESET_ALL}")
        summarizer = ContentSummarizer(model=summary_model, output_dir="summaries")

        metadata = {
            'title': video_data['title'],
            'uploader': video_data['uploader'],
            'duration': video_data['duration'],
            'url': video_data['url']
        }

        summary_data = summarizer.summarize(transcript_data['text'], metadata)
        print(f"{Fore.GREEN}[+] Summary complete{Style.RESET_ALL}\n")

        # Cleanup
        if not keep_files:
            audio_file = Path(video_data['audio_file'])
            if audio_file.exists():
                audio_file.unlink()
                print(f"{Fore.YELLOW}[*] Cleaned up audio file{Style.RESET_ALL}\n")

        # Print results
        print(f"\n{Fore.GREEN}{'='*70}")
        print(f"{Fore.GREEN}Video Processing Complete!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*70}\n")

        try:
            print(f"{Fore.WHITE}Video:{Style.RESET_ALL} {video_data['title']}")
        except UnicodeEncodeError:
            print(f"{Fore.WHITE}Video:{Style.RESET_ALL} [Title with special characters]")

        print(f"{Fore.WHITE}Transcript:{Style.RESET_ALL} {transcript_data['text_file']}")
        print(f"{Fore.WHITE}Summary:{Style.RESET_ALL} {summary_data['output_file']}\n")

        return {
            'success': True,
            'title': video_data['title'],
            'url': url,
            'transcript': transcript_data['text_file'],
            'summary': summary_data['output_file']
        }

    except Exception as e:
        print(f"{Fore.RED}[!] Error processing video: {str(e)}{Style.RESET_ALL}\n")
        return {
            'success': False,
            'url': url,
            'error': str(e)
        }


def process_playlist(url, whisper_model, summary_model, keep_files):
    """Process all videos in a playlist."""
    print_section_header("Step 4: Processing Playlist")

    try:
        # Get playlist videos
        downloader = YouTubeDownloader(output_dir="downloads")
        videos = downloader.get_playlist_videos(url)

        if not videos:
            print(f"{Fore.RED}[!] No videos found in playlist{Style.RESET_ALL}")
            return False

        # Show playlist summary
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}  PLAYLIST SUMMARY")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
        print(f"{Fore.WHITE}Total videos:{Style.RESET_ALL} {len(videos)}")
        print(f"{Fore.WHITE}Whisper model:{Style.RESET_ALL} {whisper_model}")
        print(f"{Fore.WHITE}AI model:{Style.RESET_ALL} {summary_model}\n")

        # Ask for confirmation
        confirm = input(f"{Fore.YELLOW}Process all {len(videos)} videos? (y/N): {Style.RESET_ALL}").strip().lower()
        if confirm != 'y':
            print(f"{Fore.YELLOW}[*] Cancelled{Style.RESET_ALL}")
            return False

        # Process each video
        results = []
        successful = 0
        failed = 0

        for idx, video in enumerate(videos, 1):
            try:
                print(f"\n{Fore.WHITE}Video Title:{Style.RESET_ALL} {video['title']}")
            except UnicodeEncodeError:
                print(f"\n{Fore.WHITE}Video Title:{Style.RESET_ALL} [Title with special characters]")

            result = process_single_video(
                video['url'],
                whisper_model,
                summary_model,
                keep_files,
                video_num=idx,
                total_videos=len(videos)
            )

            results.append(result)

            if result['success']:
                successful += 1
            else:
                failed += 1

        # Print final summary
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}  PLAYLIST PROCESSING COMPLETE!")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Successful:{Style.RESET_ALL} {successful}/{len(videos)}")
        if failed > 0:
            print(f"{Fore.RED}Failed:{Style.RESET_ALL} {failed}/{len(videos)}\n")

            # Show failed videos
            print(f"{Fore.RED}Failed videos:{Style.RESET_ALL}")
            for result in results:
                if not result['success']:
                    print(f"  - {result['url']}")
                    print(f"    Error: {result.get('error', 'Unknown')}\n")

        return True

    except Exception as e:
        print(f"{Fore.RED}[!] Error processing playlist: {str(e)}{Style.RESET_ALL}")
        return False


def main():
    """Main interactive interface."""
    print_header()

    # Get inputs
    url = get_youtube_url()

    # Check if it's a playlist
    downloader = YouTubeDownloader(output_dir="downloads")
    is_playlist = downloader.is_playlist(url)

    if is_playlist:
        print(f"\n{Fore.YELLOW}[*] Detected: YouTube Playlist{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}[*] Detected: Single Video{Style.RESET_ALL}")

    whisper_model = select_whisper_model()
    summary_model = select_summary_model()

    # Ask about keeping files
    keep = input(f"\n{Fore.WHITE}Keep downloaded audio files? (y/N): {Style.RESET_ALL}").strip().lower()
    keep_files = keep == 'y'

    # Process based on type
    if is_playlist:
        success = process_playlist(url, whisper_model, summary_model, keep_files)
    else:
        result = process_single_video(url, whisper_model, summary_model, keep_files)
        success = result['success']

    if success:
        # Ask if user wants to process another
        again = input(f"\n{Fore.WHITE}Process another video/playlist? (y/N): {Style.RESET_ALL}").strip().lower()
        if again == 'y':
            main()
        else:
            print(f"\n{Fore.CYAN}Thanks for using Sonopsis!{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
