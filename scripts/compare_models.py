"""
Compare different AI models for summarization.
Runs the same transcript through multiple models and saves outputs side by side.

Usage:
    python scripts/compare_models.py <transcript.md> [--title TITLE] [--url URL] [--models m1 m2 ...]
"""

import argparse
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.summarizer import ContentSummarizer, claude_cli_available
from utils.models import available_models, get_model_info

# Initialize
init(autoreset=True)
load_dotenv(override=True)


def test_model(model_id: str, transcript_text: str, video_metadata: dict):
    """Test a single model and return results."""
    info = get_model_info(model_id) or {"label": model_id, "provider": "?", "desc": ""}

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Testing: {model_id}")
    print(f"{Fore.CYAN}Provider: {info['provider']}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

    try:
        start_time = time.time()

        safe_name = model_id.replace('.', '_').replace('-', '_').replace('/', '_')
        summarizer = ContentSummarizer(
            model=model_id,
            output_dir=f"summaries/comparison_{safe_name}"
        )

        result = summarizer.summarize(transcript_text, video_metadata)
        elapsed_time = time.time() - start_time

        print(f"{Fore.GREEN}[+] Success!{Style.RESET_ALL}")
        print(f"{Fore.WHITE}    Time: {Fore.YELLOW}{elapsed_time:.2f}s{Style.RESET_ALL}")
        try:
            print(f"{Fore.WHITE}    Output: {Fore.YELLOW}{result['output_file']}{Style.RESET_ALL}")
        except UnicodeEncodeError:
            print(f"{Fore.WHITE}    Output saved to comparison directory{Style.RESET_ALL}")

        return {
            'model': model_id,
            'provider': info['provider'],
            'success': True,
            'time': elapsed_time,
            'output_file': result['output_file'],
        }

    except Exception as e:
        print(f"{Fore.RED}[!] Failed: {str(e)}{Style.RESET_ALL}")
        return {
            'model': model_id,
            'provider': info['provider'],
            'success': False,
            'error': str(e),
        }


def main():
    """Run comparison across models."""
    parser = argparse.ArgumentParser(description="Compare AI models on the same transcript")
    parser.add_argument("transcript", help="Path to a transcript file (.md or .txt)")
    parser.add_argument("--title", default=None, help="Video title for the summary header")
    parser.add_argument("--url", default="N/A", help="Video URL for the summary header")
    parser.add_argument("--models", nargs="+", default=None,
                        help="Model IDs to compare (default: every model with a configured backend)")
    args = parser.parse_args()

    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}AI Model Comparison for Video Summarization")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"{Fore.RED}[!] Transcript not found: {transcript_path}{Style.RESET_ALL}")
        sys.exit(1)

    print(f"{Fore.YELLOW}[*] Loading transcript...{Style.RESET_ALL}")
    transcript_text = transcript_path.read_text(encoding="utf-8")
    print(f"{Fore.GREEN}[+] Transcript loaded ({len(transcript_text)} characters){Style.RESET_ALL}")

    model_ids = args.models or available_models(claude_cli=claude_cli_available())
    if not model_ids:
        print(f"{Fore.RED}[!] No models available - configure an API key or install the Claude Code CLI{Style.RESET_ALL}")
        sys.exit(1)

    video_metadata = {
        'title': args.title or transcript_path.stem,
        'uploader': 'Unknown',
        'duration': 0,
        'url': args.url,
    }

    results = []
    for model_id in model_ids:
        result = test_model(model_id, transcript_text, video_metadata)
        if result:
            results.append(result)
        time.sleep(1)  # Brief pause between requests

    # Summary
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Comparison Results")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    if successful:
        print(f"{Fore.GREEN}Successful models:{Style.RESET_ALL}")
        for r in successful:
            print(f"  {Fore.YELLOW}{r['model']}{Style.RESET_ALL} ({r['provider']}) - {r['time']:.2f}s")

    if failed:
        print(f"\n{Fore.RED}Failed models:{Style.RESET_ALL}")
        for r in failed:
            print(f"  {Fore.YELLOW}{r['model']}{Style.RESET_ALL} ({r['provider']})")
            print(f"    Error: {r['error']}")

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Check the summaries/comparison_* directories to compare outputs!")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
