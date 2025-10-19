"""
Audio Transcription Module
Transcribes audio files using OpenAI's Whisper or WhisperX with speaker diarization.
"""

import os
import sys
import time
import whisper
import threading
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional
from colorama import Fore, Style


class AudioTranscriber:
    """Handles audio transcription using Whisper or WhisperX."""

    def __init__(self, model_name: str = "base", output_dir: str = "transcripts",
                 use_whisperx: bool = False, hf_token: Optional[str] = None):
        """
        Initialize the transcriber.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            output_dir: Directory to save transcripts
            use_whisperx: If True, use WhisperX with speaker diarization (requires HF token)
            hf_token: Hugging Face token for speaker diarization (required if use_whisperx=True)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._stop_progress = False
        self.use_whisperx = use_whisperx
        self.model_name = model_name
        self.hf_token = hf_token or os.getenv("HF_TOKEN")

        # Use custom Whisper cache location on E: drive
        # This allows sharing models across all projects without using C: drive space
        whisper_cache = os.getenv("WHISPER_CACHE_DIR", "E:/Coding/WhisperCache")
        os.makedirs(whisper_cache, exist_ok=True)

        if use_whisperx:
            print(f"[*] Using WhisperX with speaker diarization")
            if not self.hf_token:
                print(f"{Fore.YELLOW}[!] Warning: No HF_TOKEN found. Speaker diarization will be disabled.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}    Set HF_TOKEN environment variable or pass hf_token parameter.{Style.RESET_ALL}")
            # WhisperX models are loaded per-transcription for efficiency
            print(f"[+] WhisperX initialized (model will load on first use)")
        else:
            print(f"[*] Loading Whisper model: {model_name}")
            print(f"[*] Model cache: {whisper_cache}")
            self.model = whisper.load_model(model_name, download_root=whisper_cache)
            print(f"[+] Model loaded successfully")

    def _get_audio_duration(self, audio_file: str) -> float:
        """Get duration of audio file in seconds using ffprobe."""
        try:
            # Use ffprobe to get audio duration
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    audio_file
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data.get('format', {}).get('duration', 0))
                return duration
        except:
            pass

        return 0

    def _show_progress(self, duration: float):
        """Show progress bar during transcription with cyan styling."""
        start_time = time.time()

        # Add space above
        print()

        while not self._stop_progress:
            elapsed = time.time() - start_time

            # Estimate progress (Whisper typically processes at 0.5-2x real-time speed)
            # Using conservative estimate of 0.7x speed
            estimated_total = duration / 0.7
            percent = min((elapsed / estimated_total) * 100, 99.9) if estimated_total > 0 else 0

            # Create progress bar (50 chars wide, matching download bar)
            bar_length = 50
            filled = int(bar_length * percent / 100)
            bar = '=' * filled + '-' * (bar_length - filled)

            # Format time as MM:SS / MM:SS
            elapsed_str = self._format_time_short(elapsed)
            total_str = self._format_time_short(estimated_total)

            # Display progress with cyan colors (matching download bar)
            progress_text = f"\r{Fore.CYAN}[{bar}] {percent:.1f}% | {elapsed_str} / {total_str}{Style.RESET_ALL}"
            try:
                sys.stdout.write(progress_text)
                sys.stdout.flush()
            except UnicodeEncodeError:
                # Fallback for console encoding issues
                pass

            time.sleep(0.5)  # Update every 500ms

    @staticmethod
    def _format_time_short(seconds: float) -> str:
        """Format seconds to MM:SS."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

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

        # Route to appropriate transcription method
        if self.use_whisperx:
            return self._transcribe_whisperx(audio_path, language, podcast_mode)
        else:
            return self._transcribe_vanilla(audio_path, language, podcast_mode)

    def _transcribe_vanilla(self, audio_path: Path, language: Optional[str], podcast_mode: bool) -> Dict[str, any]:
        """Transcribe using vanilla Whisper."""
        try:
            # Get audio duration for progress estimation
            duration = self._get_audio_duration(str(audio_path))

            # Start progress bar in separate thread
            self._stop_progress = False
            progress_thread = None
            if duration > 0:
                progress_thread = threading.Thread(target=self._show_progress, args=(duration,))
                progress_thread.daemon = True
                progress_thread.start()

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

            # Stop progress bar
            self._stop_progress = True
            if progress_thread:
                progress_thread.join(timeout=1)

            # Clear the line and show completion (matching download bar)
            sys.stdout.write(f"\r{Fore.CYAN}{'-' * 80}\n{Style.RESET_ALL}")
            sys.stdout.flush()
            print()  # Space below

            # Get clean plain text transcript
            plain_text = result['text'].strip()

            # Create markdown header with metadata
            markdown_content = f"""# Transcript

**Language:** {result['language']}
**Duration:** {self._format_timestamp(result['segments'][-1]['end'] if result['segments'] else 0)}

---

{plain_text}
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
                'text': plain_text,  # Send clean text to LLM
                'language': result['language'],
                'text_file': str(md_file)
            }

        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")

    def _transcribe_whisperx(self, audio_path: Path, language: Optional[str], podcast_mode: bool) -> Dict[str, any]:
        """Transcribe using WhisperX with speaker diarization."""
        try:
            import whisperx
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"

            print(f"[*] Using device: {device}")

            # Get audio duration for progress estimation
            duration = self._get_audio_duration(str(audio_path))

            # Start progress bar in separate thread
            self._stop_progress = False
            progress_thread = None
            if duration > 0:
                progress_thread = threading.Thread(target=self._show_progress, args=(duration,))
                progress_thread.daemon = True
                progress_thread.start()

            # Load model
            model = whisperx.load_model(self.model_name, device, compute_type=compute_type)

            # Transcribe
            audio = whisperx.load_audio(str(audio_path))
            result = model.transcribe(audio, batch_size=16)

            # Stop progress bar
            self._stop_progress = True
            if progress_thread:
                progress_thread.join(timeout=1)

            # Clear the line
            sys.stdout.write(f"\r{Fore.CYAN}{'-' * 80}\n{Style.RESET_ALL}")
            sys.stdout.flush()

            # Align whisper output
            print(f"[*] Aligning transcript...")
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

            # Perform speaker diarization if HF token is available
            if self.hf_token:
                print(f"[*] Performing speaker diarization...")
                from pyannote.audio import Pipeline
                diarize_model = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self.hf_token
                ).to(torch.device(device))
                diarize_segments = diarize_model(str(audio_path))
                result = whisperx.assign_word_speakers(diarize_segments, result)

            print()  # Space below

            # Format transcript with speaker labels
            transcript_lines = []
            current_speaker = None
            current_text = []

            for segment in result.get("segments", []):
                speaker = segment.get("speaker", "UNKNOWN")
                text = segment.get("text", "").strip()

                if speaker != current_speaker:
                    # New speaker - save previous and start new
                    if current_text:
                        transcript_lines.append(f"**[{current_speaker}]** {' '.join(current_text)}\n")
                    current_speaker = speaker
                    current_text = [text]
                else:
                    # Same speaker - continue
                    current_text.append(text)

            # Add final segment
            if current_text:
                transcript_lines.append(f"**[{current_speaker}]** {' '.join(current_text)}\n")

            plain_text = '\n'.join(transcript_lines)

            # Create markdown header with metadata
            speakers_info = "With speaker diarization" if self.hf_token else "No speaker labels"
            markdown_content = f"""# Transcript

**Language:** {result.get("language", "unknown")}
**Duration:** {self._format_timestamp(duration)}
**Speakers:** {speakers_info}

---

{plain_text}
"""

            # Save as Markdown file
            md_file = self.output_dir / f"{audio_path.stem}_transcript.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"[+] Transcription complete")
            print(f"Detected language: {result.get('language', 'unknown')}")
            if self.hf_token:
                print(f"[+] Speaker diarization complete")
            try:
                print(f"[*] Saved to: {md_file}")
            except UnicodeEncodeError:
                print(f"[*] Files saved to transcripts directory")

            return {
                'text': plain_text,
                'language': result.get("language", "unknown"),
                'text_file': str(md_file)
            }

        except Exception as e:
            raise Exception(f"WhisperX transcription failed: {str(e)}")

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
