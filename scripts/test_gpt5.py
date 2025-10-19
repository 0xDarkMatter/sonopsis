"""
Quick test of GPT-5 summarization on the Brian Cox video.
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
load_dotenv()

# Configuration
TRANSCRIPT_FILE = "transcripts/Brian Cox： The incomprehensible scales that rule the Universe_transcript.txt"

print(f"{Fore.CYAN}{'='*60}")
print(f"{Fore.CYAN}Testing GPT-5 on Brian Cox Video")
print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

# Load transcript
with open(TRANSCRIPT_FILE, 'r', encoding='utf-8') as f:
    transcript_text = f.read()

print(f"{Fore.GREEN}[+] Transcript loaded ({len(transcript_text)} characters){Style.RESET_ALL}")

# Test GPT-5
print(f"\n{Fore.YELLOW}[*] Testing GPT-5...{Style.RESET_ALL}")

try:
    start_time = time.time()

    summarizer = ContentSummarizer(
        model="gpt-5",
        output_dir="summaries/comparison_gpt_5"
    )

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
    print(f"{Fore.WHITE}    Output: {Fore.YELLOW}{result['output_file']}{Style.RESET_ALL}")

except Exception as e:
    print(f"{Fore.RED}[!] Failed: {str(e)}{Style.RESET_ALL}")

print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
