"""
Shared Processing Pipeline
The download -> transcribe -> summarize flow used by both the CLI (main.py)
and the interactive interface (sonopsis.py).

Keeping this in one place stops the two front-ends drifting apart (cleanup
rules, metadata fields, engine names) - they only differ in how they collect
options and print headers.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from colorama import Fore, Style

from sonopsis.downloader import YouTubeDownloader
from sonopsis.speakers import infer_speaker_count
from sonopsis.transcriber import AudioTranscriber
from sonopsis.summarizer import ContentSummarizer

# Engines that accept a num_speakers hint
DIARIZING_ENGINES = {"parakeet-dia"}

ENGINE_DISPLAY = {
    "whisper": "Whisper",
    "whisperx": "WhisperX",
    "parakeet": "NVIDIA Parakeet",
    "parakeet-dia": "Parakeet + pyannote",
    "elevenlabs": "ElevenLabs",
    "openai": "OpenAI gpt-4o-transcribe",
}

# Engines whose accuracy depends on the selected Whisper model size
_WHISPER_SIZED_ENGINES = {"whisper", "whisperx"}


def engine_display_name(engine: str, whisper_model: str = "base") -> str:
    """Human-readable engine name with model size for Whisper-family engines."""
    name = ENGINE_DISPLAY.get(engine, "Whisper")
    if engine in _WHISPER_SIZED_ENGINES or engine not in ENGINE_DISPLAY:
        name += f" ({whisper_model})"
    return name


def find_existing_summary(url: str, summaries_dir: str = "summaries") -> Optional[Path]:
    """
    Return the path of an existing summary for this video, if one exists.

    Used by --skip-existing to make playlist runs resumable: videos that
    already produced a YT_{id}_*_summary.md are skipped instead of being
    re-downloaded and re-transcribed.
    """
    video_id = YouTubeDownloader._extract_video_id(url)
    if not video_id:
        return None
    matches = sorted(Path(summaries_dir).glob(f"YT_{video_id}_*_summary.md"))
    return matches[0] if matches else None


def process_video(
    url: str,
    whisper_model: str = "base",
    gpt_model: str = "claude-sonnet-4-6",
    analysis_mode: str = "basic",
    keep_files: bool = False,
    transcription_engine: str = "whisper",
    download_video: bool = False,
    video_num: Optional[int] = None,
    total_videos: Optional[int] = None,
    downloads_dir: str = "downloads",
    transcripts_dir: str = "transcripts",
    summaries_dir: str = "summaries",
    num_speakers: Optional[int] = None,
    auto_speakers: bool = False,
) -> Dict[str, Any]:
    """
    Process a single YouTube video: download, transcribe, and summarize.

    Returns:
        On success: {'success': True, 'title', 'url', 'video', 'transcript',
                     'summary', 'transcript_file', 'summary_file'}
        On failure: {'success': False, 'url', 'error'}
    """
    if video_num and total_videos:
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}  Processing Video {video_num}/{total_videos}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

    try:
        # Step 1: Download
        print(f"{Fore.CYAN}[1/3] Downloading {'video' if download_video else 'audio'}...{Style.RESET_ALL}")
        downloader = YouTubeDownloader(output_dir=downloads_dir)
        video_data = downloader.download_video(url, audio_only=not download_video)
        print(f"{Fore.CYAN}[+] Download complete{Style.RESET_ALL}\n")

        # Optional: infer the speaker count from metadata for diarizing
        # engines. Gated on high LLM confidence - an explicit --num-speakers
        # always wins, and no hint at all is the safe fallback.
        if (auto_speakers and num_speakers is None
                and transcription_engine in DIARIZING_ENGINES):
            print(f"{Fore.CYAN}[*] Inferring speaker count from video metadata...{Style.RESET_ALL}")
            num_speakers = infer_speaker_count(video_data)
            if num_speakers is None:
                print(f"{Fore.CYAN}[*] No confident count - diarizing unhinted{Style.RESET_ALL}")

        # Step 2: Transcribe
        engine_label = engine_display_name(transcription_engine, whisper_model)
        print(f"{Fore.CYAN}[2/3] Transcribing audio with {engine_label}...{Style.RESET_ALL}")
        transcriber = AudioTranscriber(
            model_name=whisper_model,
            output_dir=transcripts_dir,
            engine=transcription_engine,
            hf_token=os.getenv("HF_TOKEN"),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            num_speakers=num_speakers,
        )
        transcript_data = transcriber.transcribe(video_data['audio_file'])
        print(f"{Fore.CYAN}[+] Transcription complete ({transcript_data['language']}){Style.RESET_ALL}\n")

        # Step 3: Summarize
        print(f"{Fore.CYAN}[3/3] Generating summary with {gpt_model}...{Style.RESET_ALL}")
        summarizer = ContentSummarizer(model=gpt_model, output_dir=summaries_dir)

        metadata = {
            'title': video_data['title'],
            'uploader': video_data['uploader'],
            'duration': video_data['duration'],
            'url': video_data['url'],
            'upload_date': video_data.get('upload_date', 'Unknown'),
            'view_count': video_data.get('view_count', 0),
            'like_count': video_data.get('like_count', 0),
            'channel_url': video_data.get('channel_url', ''),
            'tags': video_data.get('tags', []),
            'categories': video_data.get('categories', []),
            'description': video_data.get('description', ''),
            'chapters': video_data.get('chapters', []),
            'language': video_data.get('language', ''),
            'whisper_model': whisper_model,
            'analysis_mode': analysis_mode,
        }

        summary_data = summarizer.summarize(
            transcript_data['text'],
            metadata,
            analysis_mode,
            transcription_engine=transcription_engine,
        )
        print(f"{Fore.CYAN}[+] Summary complete{Style.RESET_ALL}\n")

        # Cleanup. Never delete a file the user chose (or automation relied
        # on) to reuse - it existed before this run.
        if not keep_files and not video_data.get('reused_existing'):
            audio_file = Path(video_data['audio_file'])
            if audio_file.exists():
                audio_file.unlink()
                print(f"{Fore.CYAN}[*] Cleaned up temporary audio file{Style.RESET_ALL}\n")

        # Print results
        print(f"\n{Fore.CYAN}{'='*70}")
        if video_num and total_videos:
            print(f"{Fore.CYAN}Video {video_num}/{total_videos} Complete! ({total_videos - video_num} remaining){Style.RESET_ALL}")
        else:
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
            'video': video_data,
            'transcript': transcript_data,
            'summary': summary_data,
            'transcript_file': transcript_data['text_file'],
            'summary_file': summary_data['output_file'],
        }

    except Exception as e:
        print(f"{Fore.MAGENTA}[!] Error processing video: {str(e)}{Style.RESET_ALL}\n")
        return {
            'success': False,
            'url': url,
            'error': str(e),
        }
