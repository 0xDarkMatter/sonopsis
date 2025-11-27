"""
Compare different AI models for summarization.
Tests multiple models on the same transcript and saves results for comparison.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.summarizer import ContentSummarizer

# Initialize
init(autoreset=True)
load_dotenv(override=True)

# Configuration - Change this to the video you want to test
TRANSCRIPT_FILE = "transcripts/Brian Cox： The incomprehensible scales that rule the Universe_transcript.txt"
TRANSCRIPT_JSON = "transcripts/Brian Cox： The incomprehensible scales that rule the Universe_transcript.json"

# Models to test
MODELS = [
    # OpenAI models
    {"name": "gpt-4o-mini", "provider": "OpenAI", "notes": "Fast, cheap, good quality"},
    {"name": "gpt-4o", "provider": "OpenAI", "notes": "Balanced speed and quality"},
    {"name": "gpt-5", "provider": "OpenAI", "notes": "Latest OpenAI, PhD-level reasoning"},

    # Anthropic Claude 4.5 models (if you have API key)
    {"name": "claude-haiku-4-5-20251001", "provider": "Anthropic", "notes": "Fastest Claude 4.5, 1/3 cost of Sonnet"},
    {"name": "claude-sonnet-4-5-20250929", "provider": "Anthropic", "notes": "Best Claude, top coding model"},
]

def load_transcript():
    """Load the existing transcript."""
    # Load text
    with open(TRANSCRIPT_FILE, 'r', encoding='utf-8') as f:
        text = f.read()

    # Load metadata
    with open(TRANSCRIPT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return text, data

def test_model(model_info, transcript_text, metadata):
    """Test a single model and return results."""
    model_name = model_info['name']
    provider = model_info['provider']

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Testing: {model_name}")
    print(f"{Fore.CYAN}Provider: {provider}")
    print(f"{Fore.CYAN}Notes: {model_info['notes']}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

    # Check for required API key
    if provider == "Anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print(f"{Fore.YELLOW}[!] Skipping {model_name} - ANTHROPIC_API_KEY not found{Style.RESET_ALL}")
        return None

    if provider == "OpenAI" and not os.getenv("OPENAI_API_KEY"):
        print(f"{Fore.YELLOW}[!] Skipping {model_name} - OPENAI_API_KEY not found{Style.RESET_ALL}")
        return None

    try:
        start_time = time.time()

        # Create summarizer with specific model
        summarizer = ContentSummarizer(
            model=model_name,
            output_dir=f"summaries/comparison_{model_name.replace('.', '_').replace('-', '_')}"
        )

        # Generate summary - use metadata from transcript JSON
        try:
            import json
            with open(TRANSCRIPT_JSON, 'r', encoding='utf-8') as f:
                transcript_json = json.load(f)
        except:
            transcript_json = {}

        video_metadata = {
            'title': 'Brian Cox: The incomprehensible scales that rule the Universe',
            'uploader': 'Unknown',
            'duration': 0,
            'url': 'https://www.youtube.com/watch?v=FwpEk-fhZjY'
        }

        result = summarizer.summarize(transcript_text, video_metadata)

        elapsed_time = time.time() - start_time

        print(f"{Fore.GREEN}[+] Success!{Style.RESET_ALL}")
        print(f"{Fore.WHITE}    Time: {Fore.YELLOW}{elapsed_time:.2f}s{Style.RESET_ALL}")
        try:
            print(f"{Fore.WHITE}    Output: {Fore.YELLOW}{result['output_file']}{Style.RESET_ALL}")
        except UnicodeEncodeError:
            print(f"{Fore.WHITE}    Output saved to comparison directory{Style.RESET_ALL}")

        return {
            'model': model_name,
            'provider': provider,
            'success': True,
            'time': elapsed_time,
            'output_file': result['output_file'],
            'notes': model_info['notes']
        }

    except Exception as e:
        print(f"{Fore.RED}[!] Failed: {str(e)}{Style.RESET_ALL}")
        return {
            'model': model_name,
            'provider': provider,
            'success': False,
            'error': str(e),
            'notes': model_info['notes']
        }

def main():
    """Run comparison across all models."""
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}AI Model Comparison for Video Summarization")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

    # Check transcript exists
    if not Path(TRANSCRIPT_FILE).exists():
        print(f"{Fore.RED}[!] Transcript not found: {TRANSCRIPT_FILE}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[*] Run process_existing.py first to generate a transcript{Style.RESET_ALL}")
        return

    # Load transcript
    print(f"{Fore.YELLOW}[*] Loading transcript...{Style.RESET_ALL}")
    transcript_text, transcript_data = load_transcript()
    print(f"{Fore.GREEN}[+] Transcript loaded ({len(transcript_text)} characters){Style.RESET_ALL}")

    # Test each model
    results = []
    for model_info in MODELS:
        result = test_model(model_info, transcript_text, transcript_data)
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
            print(f"    {r['notes']}")

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
