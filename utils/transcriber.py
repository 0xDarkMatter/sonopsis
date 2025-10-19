"""
Audio Transcription Module
Transcribes audio files using OpenAI's Whisper model.
"""

import os
import whisper
from pathlib import Path
from typing import Dict, Optional


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

    def transcribe(self, audio_file: str, language: Optional[str] = None,
                   podcast_mode: bool = True) -> Dict[str, any]:
        """
        Transcribe an audio file.

        Args:
            audio_file: Path to audio file
            language: Language code (e.g., 'en', 'es'). Auto-detect if None.
            podcast_mode: If True, optimize for multi-speaker conversations

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
            # Create optimized prompt for podcast/multi-speaker content
            if podcast_mode:
                initial_prompt = (
                    "This is a professional podcast interview discussing technology, business, and innovation. "
                    "The speakers use natural conversational speech with occasional filler words. "
                    "Use proper punctuation and capitalize names, companies, products, and technical terms correctly. "
                    "Format in complete sentences with clear paragraph breaks. "
                    "Preserve meaningful pauses and emphasis while minimizing excessive filler words like um, uh, you know. "
                    "Maintain accuracy for all speakers and their distinct speaking styles."
                )
            else:
                initial_prompt = None

            # Transcribe with Whisper with enhanced settings
            transcribe_options = {
                'language': language,
                'verbose': False,
                'temperature': 0.0,  # More deterministic, less hallucination
                'compression_ratio_threshold': 2.4,  # Reject overly repetitive segments
                'logprob_threshold': -1.0,  # Reject low-confidence segments
                'no_speech_threshold': 0.6,  # Better silence detection
            }

            # Add prompt if in podcast mode
            if initial_prompt:
                transcribe_options['initial_prompt'] = initial_prompt

            result = self.model.transcribe(
                str(audio_path),
                **transcribe_options
            )

            # Create timestamped transcript in Markdown format
            timestamped_lines = []
            for seg in result['segments']:
                start_time = self._format_timestamp(seg['start'])
                end_time = self._format_timestamp(seg['end'])
                timestamped_lines.append(f"**[{start_time} -> {end_time}]** {seg['text'].strip()}")

            timestamped_text = '\n\n'.join(timestamped_lines)  # Double newline for paragraph spacing
            plain_text = result['text'].strip()

            # Create markdown header
            markdown_content = f"""# Transcript

**Language:** {result['language']}
**Duration:** {self._format_timestamp(result['segments'][-1]['end'] if result['segments'] else 0)}

---

{timestamped_text}
"""

            # Save as Markdown file
            md_file = self.output_dir / f"{audio_path.stem}_transcript.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"[+] Transcription complete")
            print(f"Detected language: {result['language']}")
            try:
                print(f"[*] Saved to: {md_file}")
            except UnicodeEncodeError:
                print(f"[*] Files saved to transcripts directory")

            return {
                'text': timestamped_text,  # Send timestamped version to LLM
                'plain_text': plain_text,  # Keep plain text available if needed
                'language': result['language'],
                'text_file': str(md_file)
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
