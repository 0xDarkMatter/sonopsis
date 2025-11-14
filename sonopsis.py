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
    # Reconfigure stdout/stderr for UTF-8
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from utils.downloader import YouTubeDownloader
from utils.transcriber import AudioTranscriber
from utils.summarizer import ContentSummarizer

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()


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


def show_menu(title, menu_items, default_selected=0):
    """Generic menu with keyboard navigation."""
    import msvcrt

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
    selected = show_menu("Select Whisper Model", menu_items, default_selected=1)  # Default to base
    models = ['tiny', 'base', 'small', 'medium', 'large']
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
    import torch

    has_hf_token = bool(os.getenv("HF_TOKEN"))
    has_elevenlabs_key = bool(os.getenv("ELEVENLABS_API_KEY"))
    has_gpu = torch.cuda.is_available()

    menu_items = [
        "Whisper - Local transcription (free, no speaker labels)",
        "WhisperX - Local with speaker diarization (free)" + ("" if has_hf_token else " [Requires HF_TOKEN]"),
        "ElevenLabs - Cloud transcription (paid, 99 languages, speaker diarization)" + ("" if has_elevenlabs_key else " [Requires API Key]")
    ]

    # Show performance info
    if not has_gpu:
        print(f"\n{Fore.YELLOW}Note: No GPU detected - running on CPU{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}      WhisperX will be 3-5x slower than Whisper on CPU{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}      Recommend: Use vanilla Whisper for faster local transcription{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}      Or use ElevenLabs for cloud-based transcription (~$0.22-0.48/hour){Style.RESET_ALL}\n")
    else:
        print(f"\n{Fore.GREEN}GPU detected - WhisperX will run efficiently{Style.RESET_ALL}\n")

    selected = show_menu("Select Transcription Engine", menu_items, default_selected=0)  # Default to Whisper

    # Map selection to engine name
    if selected == 0:
        engine = "whisper"
    elif selected == 1:
        engine = "whisperx"
        # If WhisperX selected but no token, prompt for it
        if not has_hf_token:
            token = prompt_for_hf_token()
            # Token is now saved and env reloaded, continue with WhisperX
    else:  # selected == 2
        engine = "elevenlabs"
        # If ElevenLabs selected but no API key, show warning
        if not has_elevenlabs_key:
            print(f"\n{Fore.YELLOW}{'='*70}")
            print(f"{Fore.YELLOW}[!] ElevenLabs API Key Required{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}\n")
            print(f"{Fore.CYAN}To use ElevenLabs transcription:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}1. Sign up at: https://elevenlabs.io{Style.RESET_ALL}")
            print(f"{Fore.CYAN}2. Get your API key from the dashboard{Style.RESET_ALL}")
            print(f"{Fore.CYAN}3. Add to .env file: ELEVENLABS_API_KEY=your_key_here{Style.RESET_ALL}\n")
            print(f"{Fore.YELLOW}Transcription will fail without a valid API key.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Press any key to continue anyway...{Style.RESET_ALL}")
            import msvcrt
            msvcrt.getch()

    return engine  # Returns "whisper", "whisperx", or "elevenlabs"


def select_analysis_mode_menu():
    """Interactive analysis mode selection menu."""
    menu_items = [
        "Basic - Quick summary with key topics and quotes (5 sections)",
        "Advanced - Comprehensive analysis with detailed notes (9 sections)"
    ]
    selected = show_menu("Select Analysis Mode", menu_items, default_selected=0)  # Default to Basic
    modes = ['basic', 'advanced']
    return modes[selected]


def select_summary_model_menu():
    """Interactive AI model selection menu."""
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    menu_items = []
    models = []

    if has_openai:
        menu_items.append("GPT-4o-mini - Fast, Budget-friendly")
        models.append('gpt-4o-mini')
        menu_items.append("GPT-4o - Balanced, Great quality")
        models.append('gpt-4o')
        menu_items.append("GPT-5 - PhD-level, Most accurate")
        models.append('gpt-5')

    if has_anthropic:
        menu_items.append("Claude Haiku 4.5 - Best value, Fast")
        models.append('claude-haiku-4-5-20251001')
        menu_items.append("Claude Sonnet 4.5 - Top quality")
        models.append('claude-sonnet-4-5-20250929')

    if not menu_items:
        print(f"{Fore.MAGENTA}No API keys found! Please add OPENAI_API_KEY or ANTHROPIC_API_KEY to .env{Style.RESET_ALL}")
        sys.exit(1)

    # Default to Claude Haiku if available, otherwise first option
    default_idx = 0
    if has_anthropic:
        for i, model in enumerate(models):
            if 'haiku' in model:
                default_idx = i
                break

    selected = show_menu("Select AI Model", menu_items, default_selected=default_idx)
    return models[selected]


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
        choice = input(f"\n{Fore.WHITE}Select model (1-{len(models)}) [default: Claude Sonnet 4.5]: {Style.RESET_ALL}").strip()

        if not choice:
            # Default to Claude Sonnet 4.5 if available
            if has_anthropic:
                for k, v in models.items():
                    if 'claude-sonnet-4-5-20250929' == v['id']:
                        choice = k
                        break
            else:
                choice = '1'

        if choice in models:
            selected = models[choice]
            print(f"{Fore.GREEN}[+] Selected: {selected['name']}{Style.RESET_ALL}")
            return selected['name']

        print(f"{Fore.RED}[!] Invalid choice. Please enter 1-{len(models)}.{Style.RESET_ALL}")


def process_single_video(url, whisper_model, summary_model, analysis_mode, keep_files, download_video=False, transcription_engine="whisper", video_num=None, total_videos=None):
    """Process a single video with selected models."""

    # Add video counter to header if processing multiple videos
    if video_num and total_videos:
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}  Processing Video {video_num}/{total_videos}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

    try:
        # Step 1: Download
        print(f"{Fore.CYAN}[1/3] Downloading {'video' if download_video else 'audio'}...{Style.RESET_ALL}")
        downloader = YouTubeDownloader(output_dir="downloads")
        video_data = downloader.download_video(url, audio_only=not download_video)
        print(f"{Fore.CYAN}[+] Download complete{Style.RESET_ALL}\n")

        # Step 2: Transcribe
        # Map engine to display name
        engine_names = {
            "whisper": "Whisper",
            "whisperx": "WhisperX",
            "elevenlabs": "ElevenLabs"
        }
        transcription_type = engine_names.get(transcription_engine, "Whisper")

        # Show model info for local engines, skip for ElevenLabs
        model_info = f" ({whisper_model} model)" if transcription_engine != "elevenlabs" else ""
        print(f"{Fore.CYAN}[2/3] Transcribing audio with {transcription_type}{model_info}...{Style.RESET_ALL}")

        transcriber = AudioTranscriber(
            model_name=whisper_model,
            output_dir="transcripts",
            use_whisperx=(transcription_engine == "whisperx"),
            hf_token=os.getenv("HF_TOKEN"),
            use_elevenlabs=(transcription_engine == "elevenlabs"),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY")
        )
        transcript_data = transcriber.transcribe(video_data['audio_file'])
        print(f"{Fore.CYAN}[+] Transcription complete ({transcript_data['language']}){Style.RESET_ALL}\n")

        # Step 3: Summarize
        print(f"{Fore.CYAN}[3/3] Generating summary with {summary_model}...{Style.RESET_ALL}")
        summarizer = ContentSummarizer(model=summary_model, output_dir="summaries")

        metadata = {
            'title': video_data['title'],
            'uploader': video_data['uploader'],
            'duration': video_data['duration'],
            'url': video_data['url']
        }

        summary_data = summarizer.summarize(transcript_data['text'], metadata, analysis_mode)
        print(f"{Fore.CYAN}[+] Summary complete{Style.RESET_ALL}\n")

        # Cleanup
        if not keep_files:
            audio_file = Path(video_data['audio_file'])
            if audio_file.exists():
                audio_file.unlink()
                print(f"{Fore.CYAN}[*] Cleaned up files{Style.RESET_ALL}\n")

        # Print results
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}Video Processing Complete!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}\n")

        try:
            print(f"{Fore.CYAN}Video:{Style.RESET_ALL} {video_data['title']}")
        except UnicodeEncodeError:
            print(f"{Fore.CYAN}Video:{Style.RESET_ALL} [Title with special characters]")

        print(f"{Fore.CYAN}Transcript:{Style.RESET_ALL} {transcript_data['text_file']}")
        print(f"{Fore.CYAN}Summary:{Style.RESET_ALL} {summary_data['output_file']}\n")

        return {
            'success': True,
            'title': video_data['title'],
            'url': url,
            'transcript': transcript_data['text_file'],
            'summary': summary_data['output_file']
        }

    except Exception as e:
        print(f"{Fore.MAGENTA}[!] Error processing video: {str(e)}{Style.RESET_ALL}\n")
        return {
            'success': False,
            'url': url,
            'error': str(e)
        }


def process_playlist(url, whisper_model, summary_model, analysis_mode, keep_files, download_video=False, transcription_engine="whisper"):
    """Process all videos in a playlist."""
    try:
        # Get playlist videos
        downloader = YouTubeDownloader(output_dir="downloads")
        videos = downloader.get_playlist_videos(url)

        if not videos:
            print(f"{Fore.CYAN}[!] No videos found in playlist{Style.RESET_ALL}")
            return False

        # Show playlist summary
        engine_names = {
            "whisper": "Whisper",
            "whisperx": "WhisperX",
            "elevenlabs": "ElevenLabs"
        }
        transcription_type = engine_names.get(transcription_engine, "Whisper")
        model_info = f" ({whisper_model})" if transcription_engine != "elevenlabs" else ""

        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}  PLAYLIST SUMMARY")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
        print(f"{Fore.CYAN}Total videos: {len(videos)}")
        print(f"{Fore.CYAN}Transcription: {transcription_type}{model_info}")
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

            result = process_single_video(
                video['url'],
                whisper_model,
                summary_model,
                analysis_mode,
                keep_files,
                download_video,
                transcription_engine,
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

    while True:
        # Step 1: Main menu
        choice = show_main_menu()

        if choice == 2:  # Exit (index 2 = third option)
            print(f"\n{Fore.CYAN}Thanks for using Sonopsis!{Style.RESET_ALL}\n")
            sys.exit(0)

        # Step 2: Select transcription engine (Whisper / WhisperX / ElevenLabs)
        transcription_engine = select_transcription_mode_menu()

        # Step 3: Select Whisper model (skip for ElevenLabs)
        if transcription_engine == "elevenlabs":
            whisper_model = "base"  # Not used for ElevenLabs, but needed for function signature
        else:
            whisper_model = select_whisper_model_menu()

        # Step 4: Select AI model
        summary_model = select_summary_model_menu()

        # Step 5: Select analysis mode
        analysis_mode = select_analysis_mode_menu()

        # Step 6: Get YouTube URL
        url = get_youtube_url_menu()

        # Verify the URL type matches choice
        downloader = YouTubeDownloader(output_dir="downloads")
        is_playlist = downloader.is_playlist(url)

        if choice == 0 and is_playlist:  # Selected single video but got playlist
            print(f"\n{Fore.MAGENTA}This is a playlist URL, but you selected single video. Please try again.{Style.RESET_ALL}\n")
            continue
        elif choice == 1 and not is_playlist:  # Selected playlist but got single video
            print(f"\n{Fore.MAGENTA}This is a single video URL, but you selected playlist. Please try again.{Style.RESET_ALL}\n")
            continue

        # Step 6: Ask about keeping files and video option
        keep_menu = ["Keep audio only", "Keep video file", "Delete all after processing"]
        keep_choice = show_menu("File Options?", keep_menu, default_selected=2)
        keep_files = (keep_choice != 2)
        download_video = (keep_choice == 1)

        # Process based on type
        print(f"\n{Fore.CYAN}Starting processing...{Style.RESET_ALL}\n")
        if is_playlist:
            process_playlist(url, whisper_model, summary_model, analysis_mode, keep_files, download_video, transcription_engine)
        else:
            process_single_video(url, whisper_model, summary_model, analysis_mode, keep_files, download_video, transcription_engine)

        print(f"\n{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
