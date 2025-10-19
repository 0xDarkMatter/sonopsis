"""
Compare Whisper vs WhisperX performance on the same file.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

from utils.transcriber import AudioTranscriber

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# File to test
audio_file = Path(r"E:\Projects\Coding\Sonopsis\downloads\Brian Cox： The incomprehensible scales that rule the Universe.mp3")

if not audio_file.exists():
    print(f"{Fore.RED}[!] File not found: {audio_file}{Style.RESET_ALL}")
    sys.exit(1)

file_size_mb = audio_file.stat().st_size / (1024*1024)

print(f"{Fore.CYAN}{'='*80}")
print(f"{Fore.CYAN}Whisper vs WhisperX Performance Comparison")
print(f"{Fore.CYAN}{'='*80}\n{Style.RESET_ALL}")

try:
    print(f"{Fore.GREEN}[+] Audio file: {audio_file.name}{Style.RESET_ALL}")
except UnicodeEncodeError:
    print(f"{Fore.GREEN}[+] Audio file: Brian Cox - Universe scales{Style.RESET_ALL}")
print(f"{Fore.CYAN}    Size: {file_size_mb:.1f} MB{Style.RESET_ALL}\n")

# Test 1: Vanilla Whisper
print(f"{Fore.YELLOW}{'='*80}")
print(f"{Fore.YELLOW}Test 1: Vanilla Whisper (no speaker labels)")
print(f"{Fore.YELLOW}{'='*80}\n{Style.RESET_ALL}")

start_time = time.time()

transcriber_whisper = AudioTranscriber(
    model_name="base",
    output_dir="transcripts",
    use_whisperx=False
)

try:
    transcript_whisper = transcriber_whisper.transcribe(str(audio_file))
    whisper_time = time.time() - start_time

    print(f"\n{Fore.GREEN}[+] Whisper completed in {whisper_time:.1f} seconds{Style.RESET_ALL}")
    print(f"{Fore.CYAN}    Language: {transcript_whisper['language']}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}    Output: {transcript_whisper['text_file']}{Style.RESET_ALL}\n")
except Exception as e:
    print(f"{Fore.RED}[!] Whisper failed: {str(e)}{Style.RESET_ALL}\n")
    whisper_time = None

# Test 2: WhisperX with speaker diarization
print(f"{Fore.YELLOW}{'='*80}")
print(f"{Fore.YELLOW}Test 2: WhisperX (with speaker diarization)")
print(f"{Fore.YELLOW}{'='*80}\n{Style.RESET_ALL}")

hf_token = os.getenv("HF_TOKEN")
if hf_token:
    print(f"{Fore.GREEN}[+] HF_TOKEN found - Speaker diarization enabled{Style.RESET_ALL}\n")
else:
    print(f"{Fore.YELLOW}[!] No HF_TOKEN - Will transcribe without speaker labels{Style.RESET_ALL}\n")

start_time = time.time()

transcriber_whisperx = AudioTranscriber(
    model_name="base",
    output_dir="transcripts",
    use_whisperx=True,
    hf_token=hf_token
)

try:
    transcript_whisperx = transcriber_whisperx.transcribe(str(audio_file))
    whisperx_time = time.time() - start_time

    print(f"\n{Fore.GREEN}[+] WhisperX completed in {whisperx_time:.1f} seconds{Style.RESET_ALL}")
    print(f"{Fore.CYAN}    Language: {transcript_whisperx['language']}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}    Output: {transcript_whisperx['text_file']}{Style.RESET_ALL}\n")
except Exception as e:
    print(f"{Fore.RED}[!] WhisperX failed: {str(e)}{Style.RESET_ALL}\n")
    whisperx_time = None

# Summary
print(f"{Fore.CYAN}{'='*80}")
print(f"{Fore.CYAN}Performance Summary")
print(f"{Fore.CYAN}{'='*80}\n{Style.RESET_ALL}")

if whisper_time:
    print(f"{Fore.GREEN}Whisper:   {whisper_time:.1f} seconds{Style.RESET_ALL}")
if whisperx_time:
    print(f"{Fore.GREEN}WhisperX:  {whisperx_time:.1f} seconds{Style.RESET_ALL}")

if whisper_time and whisperx_time:
    slowdown = whisperx_time / whisper_time
    print(f"\n{Fore.YELLOW}WhisperX is {slowdown:.1f}x slower than Whisper{Style.RESET_ALL}")
    print(f"{Fore.CYAN}But provides speaker labels: **[SPEAKER_00]**, **[SPEAKER_01]**, etc.{Style.RESET_ALL}\n")

print(f"{Fore.CYAN}{'='*80}\n{Style.RESET_ALL}")
