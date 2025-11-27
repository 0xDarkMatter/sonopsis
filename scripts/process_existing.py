"""
Process an existing downloaded audio file.
Used for testing transcription and summarization without re-downloading.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.transcriber import AudioTranscriber
from utils.summarizer import ContentSummarizer

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv(override=True)

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    print(f"{Fore.RED}[!] OPENAI_API_KEY not found in environment variables.{Style.RESET_ALL}")
    sys.exit(1)

# Get the audio file
audio_file = "downloads/WEAPONIZED ： EP #32 ： TEASER.mp3"

if not Path(audio_file).exists():
    print(f"{Fore.RED}[!] Audio file not found: {audio_file}{Style.RESET_ALL}")
    sys.exit(1)

print(f"{Fore.CYAN}{'='*60}")
print(f"{Fore.CYAN}Processing Existing Audio File")
print(f"{Fore.CYAN}{'='*60}\n{Style.RESET_ALL}")

# Step 1: Transcribe
print(f"{Fore.YELLOW}[*] Step 1/2: Transcribing audio...{Style.RESET_ALL}")
transcriber = AudioTranscriber(model_name="base", output_dir="transcripts")
transcript_data = transcriber.transcribe(audio_file)
print(f"{Fore.GREEN}[+] Transcription complete ({transcript_data['language']}){Style.RESET_ALL}")
try:
    print(f"{Fore.WHITE}    Saved to: {Fore.YELLOW}{transcript_data['text_file']}{Style.RESET_ALL}")
except UnicodeEncodeError:
    print(f"{Fore.WHITE}    Saved to transcripts directory{Style.RESET_ALL}")

# Step 2: Summarize
print(f"\n{Fore.YELLOW}[*] Step 2/2: Generating summary...{Style.RESET_ALL}")
summarizer = ContentSummarizer(model="gpt-4o-mini", output_dir="summaries")

# Create metadata from filename
metadata = {
    'title': 'WEAPONIZED EP #32 TEASER',
    'uploader': 'Unknown',
    'duration': 0,  # Unknown duration as 0
    'url': 'N/A'
}

summary_data = summarizer.summarize(transcript_data['text'], metadata)
print(f"{Fore.GREEN}[+] Summary generated{Style.RESET_ALL}")
try:
    print(f"{Fore.WHITE}    Saved to: {Fore.YELLOW}{summary_data['output_file']}{Style.RESET_ALL}")
except UnicodeEncodeError:
    print(f"{Fore.WHITE}    Saved to summaries directory{Style.RESET_ALL}")

print(f"\n{Fore.CYAN}{'='*60}")
print(f"{Fore.CYAN}Processing Complete!")
print(f"{Fore.CYAN}{'='*60}\n{Style.RESET_ALL}")
