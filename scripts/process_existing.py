"""
Process an existing downloaded audio file.
Used for testing transcription and summarization without re-downloading.

Usage:
    python scripts/process_existing.py <audio_file> [--whisper-model base] [--gpt-model MODEL]
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.transcriber import AudioTranscriber
from utils.summarizer import ContentSummarizer, claude_cli_available
from utils.models import DEFAULT_API_MODEL, DEFAULT_CLI_MODEL

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv(override=True)


def main():
    parser = argparse.ArgumentParser(description="Transcribe and summarize an existing audio file")
    parser.add_argument("audio_file", help="Path to the audio file to process")
    parser.add_argument("--whisper-model", default="base",
                        choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--gpt-model",
                        default=DEFAULT_CLI_MODEL if claude_cli_available() else DEFAULT_API_MODEL,
                        help="AI model for summarization")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY") and not claude_cli_available():
        print(f"{Fore.RED}[!] No summarization backend (API key or Claude Code CLI) found.{Style.RESET_ALL}")
        sys.exit(1)

    audio_file = Path(args.audio_file)
    if not audio_file.exists():
        print(f"{Fore.RED}[!] Audio file not found: {audio_file}{Style.RESET_ALL}")
        sys.exit(1)

    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Processing Existing Audio File")
    print(f"{Fore.CYAN}{'='*60}\n{Style.RESET_ALL}")

    # Step 1: Transcribe
    print(f"{Fore.YELLOW}[*] Step 1/2: Transcribing audio...{Style.RESET_ALL}")
    transcriber = AudioTranscriber(model_name=args.whisper_model, output_dir="transcripts")
    transcript_data = transcriber.transcribe(str(audio_file))
    print(f"{Fore.GREEN}[+] Transcription complete ({transcript_data['language']}){Style.RESET_ALL}")
    try:
        print(f"{Fore.WHITE}    Saved to: {Fore.YELLOW}{transcript_data['text_file']}{Style.RESET_ALL}")
    except UnicodeEncodeError:
        print(f"{Fore.WHITE}    Saved to transcripts directory{Style.RESET_ALL}")

    # Step 2: Summarize
    print(f"\n{Fore.YELLOW}[*] Step 2/2: Generating summary...{Style.RESET_ALL}")
    summarizer = ContentSummarizer(model=args.gpt_model, output_dir="summaries")
    metadata = {
        'title': audio_file.stem,
        'uploader': 'Unknown',
        'duration': 0,
        'url': 'N/A',
        'analysis_mode': 'basic',
        'whisper_model': args.whisper_model,
    }
    summary_data = summarizer.summarize(transcript_data['text'], metadata, 'basic')
    print(f"{Fore.GREEN}[+] Summary complete{Style.RESET_ALL}")
    print(f"{Fore.WHITE}    Saved to: {Fore.YELLOW}{summary_data['output_file']}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
