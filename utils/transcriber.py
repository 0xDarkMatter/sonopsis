"""
Audio Transcription Module
Transcribes audio files using OpenAI's Whisper model.
"""

import os
import whisper
from pathlib import Path
from typing import Dict, Optional
import json


class AudioTranscriber:
    """Handles audio transcription using Whisper."""

    def __init__(self, model_name: str = "base", output_dir: str = "transcripts"):
        """
        Initialize the transcriber.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            output_dir: Directory to save transcripts
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Use custom Whisper cache location on E: drive
        # This allows sharing models across all projects without using C: drive space
        whisper_cache = os.getenv("WHISPER_CACHE_DIR", "E:/Coding/WhisperCache")
        os.makedirs(whisper_cache, exist_ok=True)

        print(f"[*] Loading Whisper model: {model_name}")
        print(f"[*] Model cache: {whisper_cache}")
        self.model = whisper.load_model(model_name, download_root=whisper_cache)
        print(f"[+] Model loaded successfully")

    def transcribe(self, audio_file: str, language: Optional[str] = None) -> Dict[str, any]:
        """
        Transcribe an audio file.

        Args:
            audio_file: Path to audio file
            language: Language code (e.g., 'en', 'es'). Auto-detect if None.

        Returns:
            Dictionary containing transcription results

        Raises:
            Exception: If transcription fails
        """
        audio_path = Path(audio_file)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        try:
            print(f"[*] Transcribing: {audio_path.name}")
        except UnicodeEncodeError:
            # Fallback for console encoding issues
            print(f"[*] Transcribing audio file...")

        try:
            # Transcribe with Whisper
            result = self.model.transcribe(
                str(audio_path),
                language=language,
                verbose=False
            )

            # Prepare output
            transcript_data = {
                'text': result['text'].strip(),
                'language': result['language'],
                'segments': [
                    {
                        'start': seg['start'],
                        'end': seg['end'],
                        'text': seg['text'].strip()
                    }
                    for seg in result['segments']
                ]
            }

            # Save transcript
            transcript_file = self.output_dir / f"{audio_path.stem}_transcript.json"
            with open(transcript_file, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)

            # Also save plain text version
            text_file = self.output_dir / f"{audio_path.stem}_transcript.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(transcript_data['text'])

            print(f"[+] Transcription complete")
            try:
                print(f"[*] Saved to: {transcript_file}")
                print(f"[*] Plain text: {text_file}")
            except UnicodeEncodeError:
                print(f"[*] Files saved to transcripts directory")

            return {
                'text': transcript_data['text'],
                'language': transcript_data['language'],
                'segments': transcript_data['segments'],
                'transcript_file': str(transcript_file),
                'text_file': str(text_file)
            }

        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")

    def transcribe_with_timestamps(self, audio_file: str) -> str:
        """
        Create a formatted transcript with timestamps.

        Args:
            audio_file: Path to audio file

        Returns:
            Formatted transcript string with timestamps
        """
        result = self.transcribe(audio_file)

        formatted_lines = []
        for segment in result['segments']:
            start_time = self._format_timestamp(segment['start'])
            end_time = self._format_timestamp(segment['end'])
            formatted_lines.append(f"[{start_time} -> {end_time}] {segment['text']}")

        return '\n'.join(formatted_lines)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
