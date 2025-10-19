"""
Test script to process a plain text transcript without timestamps.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

from utils.summarizer import ContentSummarizer

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Read the plain text transcript file
transcript_file = Path(r"E:\Projects\Coding\Sonopsis\transcripts\NASA & UFOs： Pagan Rituals, Secret Science & Time Travel_transcript.txt")

if not transcript_file.exists():
    print(f"{Fore.RED}[!] Transcript file not found: {transcript_file}{Style.RESET_ALL}")
    sys.exit(1)

print(f"{Fore.CYAN}{'='*70}")
print(f"{Fore.CYAN}Testing Advanced Summary on Plain Text Transcript")
print(f"{Fore.CYAN}{'='*70}\n{Style.RESET_ALL}")

# Read transcript content
with open(transcript_file, 'r', encoding='utf-8') as f:
    transcript_text = f.read()

print(f"{Fore.GREEN}[+] Loaded transcript from file{Style.RESET_ALL}")
print(f"{Fore.CYAN}    File size: {len(transcript_text):,} characters{Style.RESET_ALL}")
print(f"{Fore.CYAN}    Word count: ~{len(transcript_text.split()):,} words{Style.RESET_ALL}\n")

# Create metadata from the file
metadata = {
    'title': 'NASA & UFOs: Pagan Rituals, Secret Science & Time Travel',
    'uploader': 'American Alchemy',
    'duration': 3600,  # Approximate duration (1 hour)
    'url': 'https://www.youtube.com/watch?v=example'
}

print(f"{Fore.YELLOW}Processing with advanced mode...{Style.RESET_ALL}")
print(f"{Fore.CYAN}Model: gpt-4o-mini{Style.RESET_ALL}\n")

# Summarize using advanced mode
summarizer = ContentSummarizer(model="gpt-4o-mini", output_dir="summaries")

try:
    summary_data = summarizer.summarize(transcript_text, metadata, analysis_mode="advanced")

    print(f"\n{Fore.GREEN}[+] Summary generated successfully!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}    Output file: {summary_data['output_file']}{Style.RESET_ALL}\n")

    # Show summary stats
    summary_length = len(summary_data['summary'])
    print(f"{Fore.CYAN}    Summary length: {summary_length:,} characters{Style.RESET_ALL}")
    print(f"{Fore.CYAN}    Compression ratio: {len(transcript_text)/summary_length:.1f}x{Style.RESET_ALL}\n")

except Exception as e:
    print(f"\n{Fore.RED}[!] Error during summarization: {str(e)}{Style.RESET_ALL}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"{Fore.CYAN}{'='*70}")
print(f"{Fore.CYAN}Test Complete!")
print(f"{Fore.CYAN}{'='*70}\n{Style.RESET_ALL}")
