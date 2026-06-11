"""
Sonopsis - Interactive YouTube Video Summarizer
User-friendly interface with model selection menus.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from utils.config import default_engine, load_config
from utils.downloader import YouTubeDownloader
from utils.models import MODELS, available_models
from utils.pipeline import engine_display_name, process_video
from utils.summarizer import claude_cli_available

# Arrow-key menus need msvcrt (Windows-only); everywhere else we fall back
# to numbered input so the interactive mode still works on macOS/Linux
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv(override=True)  # .env takes precedence over system env vars

CONFIG = load_config()


def print_banner():
    """Print application banner with border - Claude Code style."""
    width = 100
    title = "Sonopsis v1.0"

    # Top border with title
    title_padding = width - len(title) - 5
    border_top = f"╭─── {title} " + "─" * title_padding + "╮"

    # ASCII logo lines with padding of 2 spaces
    logo_lines = [
        "███████╗ ██████╗ ███╗   ██╗ ██████╗ ██████╗ ███████╗██╗███████╗",
        "██╔════╝██╔═══██╗████╗  ██║██╔═══██╗██╔══██╗██╔════╝██║██╔════╝",
        "███████╗██║   ██║██╔██╗ ██║██║   ██║██████╔╝███████╗██║███████╗",
        "╚════██║██║   ██║██║╚██╗██║██║   ██║██╔═══╝ ╚════██║██║╚════██║",
        "███████║╚██████╔╝██║ ╚████║╚██████╔╝██║     ███████║██║███████║",
        "╚══════╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝╚══════╝"
    ]

    # Text to display on the right of logo
    text_lines = [
        "",
        "",
        "Sonopsis v1.0",
        "Video/Audio Summariser",
        "",
        ""
    ]

    print(f"\n{Fore.CYAN}{border_top}")
    print(f"{Fore.CYAN}│{' ' * width}│")

    # Print logo with text on the right side
    for i, logo_line in enumerate(logo_lines):
        text = text_lines[i]
        # Logo is 68 chars, we need: 2 (left pad) + 68 (logo) + 2 (separator) + text + spaces = 100
        spaces_needed = width - 2 - len(logo_line) - 2 - len(text)
        print(f"{Fore.CYAN}│  {logo_line}  {text}{' ' * spaces_needed}│{Style.RESET_ALL}")

    print(f"{Fore.CYAN}│{' ' * width}│")

    # Bottom border
    border_bottom = "╰" + "─" * width + "╯"
    print(f"{Fore.CYAN}{border_bottom}{Style.RESET_ALL}\n")


def print_section_header(title):
    """Print a section header."""
    print(f"\n{Fore.YELLOW}{'-'*70}")
    print(f"{Fore.YELLOW}{title}")
    print(f"{Fore.YELLOW}{'-'*70}{Style.RESET_ALL}\n")


def _show_menu_numbered(title, menu_items, default_selected=0):
    """Cross-platform fallback menu: numbered list with input()."""
    print(f"\n{Fore.CYAN}{'─'*70}")
    print(f"{Fore.CYAN}{title}")
    print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
    for i, item in enumerate(menu_items):
        marker = " (default)" if i == default_selected else ""
        print(f"{Fore.GREEN}[{i+1}]{Style.RESET_ALL} {item}{Fore.YELLOW}{marker}{Style.RESET_ALL}")

    while True:
        choice = input(f"\n{Fore.CYAN}Select (1-{len(menu_items)}) [default: {default_selected + 1}]: {Style.RESET_ALL}").strip()
        if not choice:
            return default_selected
        if choice.isdigit() and 1 <= int(choice) <= len(menu_items):
            return int(choice) - 1
        print(f"{Fore.RED}[!] Invalid choice. Enter 1-{len(menu_items)}.{Style.RESET_ALL}")


def show_menu(title, menu_items, default_selected=0):
    """Generic menu with keyboard navigation (numbered fallback off-Windows)."""
    if not HAS_MSVCRT or not sys.stdin.isatty():
        return _show_menu_numbered(title, menu_items, default_selected)

    width = 100
    selected = default_selected

    # Calculate fixed hover width (longest item + 5 chars)
    max_item_len = max(len(f"[{i+1}] {item}") for i, item in enumerate(menu_items))
    hover_width = max_item_len + 5

    # Top border with title
    title_padding = width - len(title) - 5
    border_top = f"╭─── {title} " + "─" * title_padding + "╮"
    border_bottom = "╰" + "─" * width + "╯"

    def render_menu():
        """Render the menu with current selection."""
        # Save current position, move to start of first menu item
        print(f"\0337", end='')  # Save cursor position

        # Move up: from instruction line to first menu item
        # Layout: border_bottom, empty_line, menu_items..., empty_line, border_top
        # From instruction to first menu item = border + empty + all menu items
        num_lines_up = len(menu_items) + 2
        print(f"\033[{num_lines_up}A\r", end='')  # Move up and to start of line

        # Redraw ONLY the menu items
        for i, item in enumerate(menu_items):
            item_text = f"[{i+1}] {item}"
            if i == selected:
                # Black text on cyan background
                highlight_spaces = hover_width - len(item_text)
                remaining_spaces = width - hover_width - 2
                print(f"{Fore.CYAN}│  \033[30m\033[46m{item_text}{' ' * highlight_spaces}\033[0m{Fore.CYAN}{' ' * remaining_spaces}│{Style.RESET_ALL}")
            else:
                spaces = width - len(item_text) - 2
                print(f"{Fore.CYAN}│  {item_text}{' ' * spaces}│{Style.RESET_ALL}")

        # Restore cursor position
        print(f"\0338", end='', flush=True)

    # Initial render
    print(f"\n{Fore.CYAN}{border_top}")
    print(f"{Fore.CYAN}│{' ' * width}│")
    for i, item in enumerate(menu_items):
        item_text = f"[{i+1}] {item}"
        if i == selected:
            # Black text on cyan background
            highlight_spaces = hover_width - len(item_text)
            remaining_spaces = width - hover_width - 2
            print(f"{Fore.CYAN}│  \033[30m\033[46m{item_text}{' ' * highlight_spaces}\033[0m{Fore.CYAN}{' ' * remaining_spaces}│{Style.RESET_ALL}")
        else:
            spaces = width - len(item_text) - 2
            print(f"{Fore.CYAN}│  {item_text}{' ' * spaces}│{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│{' ' * width}│")  # Empty line before border
    print(f"{Fore.CYAN}{border_bottom}{Style.RESET_ALL}")
    print(f"{Style.BRIGHT}{Fore.CYAN}Use ↑/↓ arrows or TAB to navigate, ENTER to select{Style.RESET_ALL}", end='', flush=True)

    while True:
        key = msvcrt.getch()

        if key == b'\xe0':  # Arrow key prefix
            key = msvcrt.getch()
            if key == b'H':  # Up arrow
                selected = (selected - 1) % len(menu_items)
                render_menu()
            elif key == b'P':  # Down arrow
                selected = (selected + 1) % len(menu_items)
                render_menu()
        elif key == b'\t':  # Tab
            selected = (selected + 1) % len(menu_items)
            render_menu()
        elif key == b'\r':  # Enter
            print()  # New line after selection
            return selected
        elif key.isdigit():  # Direct number selection
            num = int(key.decode()) - 1
            if 0 <= num < len(menu_items):
                print()
                return num


def show_main_menu():
    """Display main menu."""
    menu_items = [
        "Process single video",
        "Process playlist",
        "Exit"
    ]
    return show_menu("Main Menu", menu_items)


def select_whisper_model_menu():
    """Interactive Whisper model selection menu."""
    menu_items = [
        "tiny - Fast, 75MB, Good quality",
        "base - Recommended, 150MB, Better quality",
        "small - Medium speed, 500MB, Great quality",
        "medium - Slow, 1.5GB, Excellent quality",
        "large - Slowest, 3GB, Best quality"
    ]
    models = ['tiny', 'base', 'small', 'medium', 'large']
    config_default = CONFIG['defaults'].get('whisper_model', 'base')
    default_idx = models.index(config_default) if config_default in models else 1
    selected = show_menu("Select Whisper Model", menu_items, default_selected=default_idx)
    return models[selected]


def prompt_for_hf_token():
    """Prompt user for Hugging Face token and save to .env file."""
    width = 100
    title = "Hugging Face Token Required"

    title_padding = width - len(title) - 5
    border_top = f"╭─── {title} " + "─" * title_padding + "╮"
    border_bottom = "╰" + "─" * width + "╯"

    print(f"\n{Fore.YELLOW}{border_top}")
    print(f"{Fore.YELLOW}│{' ' * width}│")
    print(f"{Fore.YELLOW}│  WhisperX speaker diarization requires a Hugging Face token.{' ' * 40}│")
    print(f"{Fore.YELLOW}│{' ' * width}│")
    print(f"{Fore.YELLOW}│  Get your free token at: {Fore.CYAN}https://huggingface.co/settings/tokens{' ' * 33}{Fore.YELLOW}│")
    print(f"{Fore.YELLOW}│{' ' * width}│")
    print(f"{Fore.YELLOW}│  Without a token, WhisperX will work but won't identify speakers.{' ' * 34}│")
    print(f"{Fore.YELLOW}│{' ' * width}│")
    print(f"{Fore.YELLOW}{border_bottom}{Style.RESET_ALL}\n")

    while True:
        choice = input(f"{Fore.CYAN}Enter your HF token (or press Enter to skip): {Style.RESET_ALL}").strip()

        if not choice:
            print(f"\n{Fore.YELLOW}[!] Continuing without speaker diarization.{Style.RESET_ALL}\n")
            return None

        # Basic validation - HF tokens start with "hf_"
        if not choice.startswith("hf_"):
            print(f"{Fore.RED}[!] Invalid token format. HF tokens should start with 'hf_'{Style.RESET_ALL}")
            retry = input(f"{Fore.CYAN}Try again? (y/N): {Style.RESET_ALL}").strip().lower()
            if retry != 'y':
                return None
            continue

        # Save to .env file
        try:
            env_file = Path(".env")

            # Check if HF_TOKEN already exists in .env
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if 'HF_TOKEN=' in content:
                    # Update existing token
                    lines = content.split('\n')
                    new_lines = []
                    for line in lines:
                        if line.startswith('HF_TOKEN='):
                            new_lines.append(f'HF_TOKEN={choice}')
                        else:
                            new_lines.append(line)

                    with open(env_file, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines))
                else:
                    # Append new token
                    with open(env_file, 'a', encoding='utf-8') as f:
                        if not content.endswith('\n'):
                            f.write('\n')
                        f.write(f'\n# Hugging Face API token for WhisperX speaker diarization\n')
                        f.write(f'# Get your token at: https://huggingface.co/settings/tokens\n')
                        f.write(f'# Required for PyAnnote speaker diarization with WhisperX\n')
                        f.write(f'HF_TOKEN={choice}\n')
            else:
                # Create new .env file
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(f'# Hugging Face API token for WhisperX speaker diarization\n')
                    f.write(f'# Get your token at: https://huggingface.co/settings/tokens\n')
                    f.write(f'# Required for PyAnnote speaker diarization with WhisperX\n')
                    f.write(f'HF_TOKEN={choice}\n')

            # Reload environment variables
            load_dotenv(override=True)

            print(f"\n{Fore.GREEN}[+] Token saved to .env file successfully!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[+] Speaker diarization enabled.{Style.RESET_ALL}\n")
            return choice

        except Exception as e:
            print(f"{Fore.RED}[!] Error saving token: {str(e)}{Style.RESET_ALL}")
            return None


def select_transcription_mode_menu():
    """Interactive transcription mode selection menu."""
    # torch is an optional extra (uv sync --extra whisper); without it only
    # ElevenLabs cloud transcription is usable
    try:
        import torch
        has_torch = True
        has_gpu = torch.cuda.is_available()
    except ImportError:
        has_torch = False
        has_gpu = False

    try:
        import onnx_asr  # noqa: F401
        has_parakeet = True
    except ImportError:
        has_parakeet = False

    has_hf_token = bool(os.getenv("HF_TOKEN"))
    has_elevenlabs_key = bool(os.getenv("ELEVENLABS_API_KEY"))
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))

    menu_items = [
        "Whisper - Local transcription (free, no speaker labels)" + ("" if has_torch else " [Requires: uv sync --extra whisper]"),
        "WhisperX - Local with speaker diarization (free)" + ("" if has_hf_token else " [Requires HF_TOKEN]") + ("" if has_torch else " [Requires: uv sync --extra whisper]"),
        "Parakeet - Local, beats Whisper accuracy, no PyTorch (free)" + ("" if has_parakeet else " [Requires: uv sync --extra parakeet]"),
        "ElevenLabs - Cloud transcription (paid, 99 languages, speaker diarization)" + ("" if has_elevenlabs_key else " [Requires API Key]"),
        "OpenAI - Cloud gpt-4o-transcribe with speaker diarization (paid)" + ("" if has_openai_key else " [Requires OPENAI_API_KEY]")
    ]

    # Show performance info
    if not has_torch:
        print(f"\n{Fore.YELLOW}Note: PyTorch/Whisper not installed - local transcription unavailable{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}      Install with: uv sync --extra whisper{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}      Or use ElevenLabs for cloud transcription (no local models needed){Style.RESET_ALL}\n")
    elif not has_gpu:
        print(f"\n{Fore.YELLOW}Note: No GPU detected - running on CPU{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}      WhisperX will be 3-5x slower than Whisper on CPU{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}      Recommend: Use vanilla Whisper for faster local transcription{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}      Or use ElevenLabs for cloud-based transcription (~$0.22-0.48/hour){Style.RESET_ALL}\n")
    else:
        print(f"\n{Fore.GREEN}GPU detected - WhisperX will run efficiently{Style.RESET_ALL}\n")

    engines = ["whisper", "whisperx", "parakeet", "elevenlabs", "openai"]
    config_default = default_engine(CONFIG['defaults'].get('transcription_engine'))
    default_idx = engines.index(config_default) if config_default in engines else 0
    selected = show_menu("Select Transcription Engine", menu_items, default_selected=default_idx)
    engine = engines[selected]

    if engine == "whisperx" and not has_hf_token:
        # If WhisperX selected but no token, prompt for it
        prompt_for_hf_token()
    elif engine == "elevenlabs" and not has_elevenlabs_key:
        print(f"\n{Fore.YELLOW}{'='*70}")
        print(f"{Fore.YELLOW}[!] ElevenLabs API Key Required{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}\n")
        print(f"{Fore.CYAN}To use ElevenLabs transcription:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}1. Sign up at: https://elevenlabs.io{Style.RESET_ALL}")
        print(f"{Fore.CYAN}2. Get your API key from the dashboard{Style.RESET_ALL}")
        print(f"{Fore.CYAN}3. Add to .env file: ELEVENLABS_API_KEY=your_key_here{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}Transcription will fail without a valid API key.{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Press ENTER to continue anyway...{Style.RESET_ALL}")

    return engine


def select_analysis_mode_menu():
    """Interactive analysis mode selection menu."""
    menu_items = [
        "Basic - Quick summary with key topics and quotes (5 sections)",
        "Advanced - Comprehensive analysis with detailed notes (9 sections)"
    ]
    modes = ['basic', 'advanced']
    config_default = CONFIG['defaults'].get('analysis_mode', 'basic')
    default_idx = modes.index(config_default) if config_default in modes else 0
    selected = show_menu("Select Analysis Mode", menu_items, default_selected=default_idx)
    return modes[selected]


def select_summary_model_menu():
    """Interactive AI model selection menu, driven by the model registry."""
    has_claude_cli = claude_cli_available()
    model_ids = available_models(claude_cli=has_claude_cli)

    if not model_ids:
        print(f"{Fore.MAGENTA}No summarization backend found!{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}Add OPENAI_API_KEY, ANTHROPIC_API_KEY or OPENROUTER_API_KEY to .env, "
              f"or install the Claude Code CLI.{Style.RESET_ALL}")
        sys.exit(1)

    menu_items = []
    for model_id in model_ids:
        info = MODELS[model_id]
        menu_items.append(f"{info['label']} - {info['quality']}, {info['speed']}, {info['cost']}")

    # Default: Claude Code CLI if installed (subscription, no API cost),
    # else the configured default model, else the first option
    default_idx = 0
    config_default = CONFIG['defaults'].get('summary_model')
    if not has_claude_cli and config_default in model_ids:
        default_idx = model_ids.index(config_default)

    selected = show_menu("Select AI Model", menu_items, default_selected=default_idx)
    return model_ids[selected]


def get_youtube_url_menu():
    """Get YouTube URL from user with styled prompt."""
    width = 100
    title = "Enter YouTube URL"

    title_padding = width - len(title) - 5
    border_top = f"╭─── {title} " + "─" * title_padding + "╮"
    border_bottom = "╰" + "─" * width + "╯"

    print(f"\n{Fore.CYAN}{border_top}")
    print(f"{Fore.CYAN}│{' ' * width}│")
    print(f"{Fore.CYAN}│  Enter the YouTube video or playlist URL:{' ' * 58}│")
    print(f"{Fore.CYAN}│{' ' * width}│")
    print(f"{Fore.CYAN}{border_bottom}{Style.RESET_ALL}\n")

    while True:
        url = input(f"{Fore.CYAN}URL: {Style.RESET_ALL}").strip()

        if url.lower() == 'q':
            sys.exit(0)

        if 'youtube.com' in url or 'youtu.be' in url:
            return url

        print(f"{Fore.MAGENTA}Invalid URL. Please enter a valid YouTube URL.{Style.RESET_ALL}")


def process_playlist(url, whisper_model, summary_model, analysis_mode, keep_files,
                     download_video=False, transcription_engine="whisper"):
    """Process all videos in a playlist."""
    paths = CONFIG['paths']
    try:
        # Get playlist videos
        downloader = YouTubeDownloader(output_dir=paths['downloads'])
        videos = downloader.get_playlist_videos(url)

        if not videos:
            print(f"{Fore.CYAN}[!] No videos found in playlist{Style.RESET_ALL}")
            return False

        # Show playlist summary
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}  PLAYLIST SUMMARY")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
        print(f"{Fore.CYAN}Total videos: {len(videos)}")
        print(f"{Fore.CYAN}Transcription: {engine_display_name(transcription_engine, whisper_model)}")
        print(f"{Fore.CYAN}AI model: {summary_model}")
        print(f"{Fore.CYAN}Analysis mode: {analysis_mode}\n")

        # Ask for confirmation
        confirm = input(f"{Fore.CYAN}Process all {len(videos)} videos? (y/N): {Style.RESET_ALL}").strip().lower()
        if confirm != 'y':
            print(f"{Fore.CYAN}[*] Cancelled{Style.RESET_ALL}")
            return False

        # Process each video
        results = []
        successful = 0
        failed = 0

        for idx, video in enumerate(videos, 1):
            try:
                print(f"\n{Fore.CYAN}Video Title: {video['title']}{Style.RESET_ALL}")
            except UnicodeEncodeError:
                print(f"\n{Fore.CYAN}Video Title: [Title with special characters]{Style.RESET_ALL}")

            result = process_video(
                video['url'],
                whisper_model=whisper_model,
                gpt_model=summary_model,
                analysis_mode=analysis_mode,
                keep_files=keep_files,
                transcription_engine=transcription_engine,
                download_video=download_video,
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

        # Print final summary
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}  PLAYLIST PROCESSING COMPLETE!")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

        print(f"{Fore.CYAN}Successful: {successful}/{len(videos)}")
        if failed > 0:
            print(f"{Fore.CYAN}Failed: {failed}/{len(videos)}\n")

            # Show failed videos
            print(f"{Fore.CYAN}Failed videos:{Style.RESET_ALL}")
            for result in results:
                if not result['success']:
                    print(f"  - {result['url']}")
                    print(f"    Error: {result.get('error', 'Unknown')}\n")

        return True

    except Exception as e:
        print(f"{Fore.MAGENTA}[!] Error processing playlist: {str(e)}{Style.RESET_ALL}")
        return False


def main():
    """Main interactive interface."""
    print_banner()
    paths = CONFIG['paths']

    while True:
        # Step 1: Main menu
        choice = show_main_menu()

        if choice == 2:  # Exit (index 2 = third option)
            print(f"\n{Fore.CYAN}Thanks for using Sonopsis!{Style.RESET_ALL}\n")
            sys.exit(0)

        # Step 2: Select transcription engine (Whisper / WhisperX / ElevenLabs)
        transcription_engine = select_transcription_mode_menu()

        # Step 3: Select Whisper model (only relevant for Whisper-family engines)
        if transcription_engine in ("whisper", "whisperx"):
            whisper_model = select_whisper_model_menu()
        else:
            whisper_model = "base"  # Unused by parakeet/elevenlabs/openai, needed for signature

        # Step 4: Select AI model
        summary_model = select_summary_model_menu()

        # Step 5: Select analysis mode
        analysis_mode = select_analysis_mode_menu()

        # Step 6: Get YouTube URL
        url = get_youtube_url_menu()

        # Verify the URL type matches choice
        is_playlist = YouTubeDownloader.is_playlist(url)

        if choice == 0 and is_playlist:  # Selected single video but got playlist
            print(f"\n{Fore.MAGENTA}This is a playlist URL, but you selected single video. Please try again.{Style.RESET_ALL}\n")
            continue
        elif choice == 1 and not is_playlist:  # Selected playlist but got single video
            print(f"\n{Fore.MAGENTA}This is a single video URL, but you selected playlist. Please try again.{Style.RESET_ALL}\n")
            continue

        # Step 7: Ask about keeping files and video option
        keep_menu = ["Keep audio only", "Keep video file", "Delete all after processing"]
        keep_choice = show_menu("File Options?", keep_menu, default_selected=2)
        keep_files = (keep_choice != 2)
        download_video = (keep_choice == 1)

        # Process based on type
        print(f"\n{Fore.CYAN}Starting processing...{Style.RESET_ALL}\n")
        if is_playlist:
            process_playlist(url, whisper_model, summary_model, analysis_mode, keep_files,
                             download_video, transcription_engine)
        else:
            process_video(
                url,
                whisper_model=whisper_model,
                gpt_model=summary_model,
                analysis_mode=analysis_mode,
                keep_files=keep_files,
                transcription_engine=transcription_engine,
                download_video=download_video,
                downloads_dir=paths['downloads'],
                transcripts_dir=paths['transcripts'],
                summaries_dir=paths['summaries'],
            )

        print(f"\n{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
