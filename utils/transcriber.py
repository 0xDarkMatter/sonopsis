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
                 use_whisperx: bool = False, hf_token: Optional[str] = None,
                 use_elevenlabs: bool = False, elevenlabs_api_key: Optional[str] = None):
        """
        Initialize the transcriber.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            output_dir: Directory to save transcripts
            use_whisperx: If True, use WhisperX with speaker diarization (requires HF token)
            hf_token: Hugging Face token for speaker diarization (required if use_whisperx=True)
            use_elevenlabs: If True, use ElevenLabs cloud transcription
            elevenlabs_api_key: ElevenLabs API key (required if use_elevenlabs=True)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._stop_progress = False
        self.use_whisperx = use_whisperx
        self.use_elevenlabs = use_elevenlabs
        self.model_name = model_name
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")

        # Use custom Whisper cache location on E: drive
        # This allows sharing models across all projects without using C: drive space
        whisper_cache = os.getenv("WHISPER_CACHE_DIR", "E:/Coding/WhisperCache")
        os.makedirs(whisper_cache, exist_ok=True)

        if use_elevenlabs:
            print(f"[*] Using ElevenLabs cloud transcription (99 languages, speaker diarization)")
            if not self.elevenlabs_api_key:
                print(f"{Fore.YELLOW}[!] Warning: No ELEVENLABS_API_KEY found.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}    Set ELEVENLABS_API_KEY environment variable or pass elevenlabs_api_key parameter.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}    Transcription will fail without a valid API key.{Style.RESET_ALL}")
            print(f"[+] ElevenLabs initialized")
            self.model = None  # No local model needed for ElevenLabs
        elif use_whisperx:
            print(f"[*] Using WhisperX with speaker diarization")
            if not self.hf_token:
                print(f"{Fore.YELLOW}[!] Warning: No HF_TOKEN found. Speaker diarization will be disabled.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}    Set HF_TOKEN environment variable or pass hf_token parameter.{Style.RESET_ALL}")
            # WhisperX models are loaded per-transcription for efficiency
            print(f"[+] WhisperX initialized (model will load on first use)")

            # Load vanilla Whisper as fallback in case WhisperX fails (CUDA issues, etc.)
            print(f"[*] Loading vanilla Whisper as fallback: {model_name}")
            print(f"[*] Model cache: {whisper_cache}")
            self.model = whisper.load_model(model_name, download_root=whisper_cache)
            print(f"[+] Fallback model loaded successfully")
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
        if self.use_elevenlabs:
            return self._transcribe_elevenlabs(audio_path, language, podcast_mode)
        elif self.use_whisperx:
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
        """Transcribe using WhisperX with speaker diarization. Falls back to vanilla Whisper on failure."""
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
            error_msg = str(e).lower()

            # Detect CUDA library issues
            if any(keyword in error_msg for keyword in ['cublas', 'cuda', 'cudnn', 'library', '.dll', '.so']):
                print(f"\n{Fore.YELLOW}{'='*70}")
                print(f"{Fore.YELLOW}[!] WhisperX CUDA Library Error Detected{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}\n")

                print(f"{Fore.YELLOW}Problem: WhisperX requires CUDA 12.x libraries, but PyTorch has CUDA 11.8{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Error: {str(e)[:150]}{Style.RESET_ALL}\n")

                print(f"{Fore.CYAN}Solution Options:{Style.RESET_ALL}")
                print(f"{Fore.CYAN}1. Install compatible ctranslate2 for CUDA 11.8:{Style.RESET_ALL}")
                print(f"   pip install ctranslate2==3.24.0")
                print(f"{Fore.CYAN}2. Upgrade PyTorch to CUDA 12.x:{Style.RESET_ALL}")
                print(f"   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
                print(f"{Fore.CYAN}3. Use CPU-only mode (slower):{Style.RESET_ALL}")
                print(f"   pip install ctranslate2 --force-reinstall --no-deps\n")

                print(f"{Fore.GREEN}[*] Falling back to vanilla Whisper for this transcription...{Style.RESET_ALL}\n")

            # Detect import errors (missing dependencies)
            elif 'import' in error_msg or 'module' in error_msg:
                print(f"\n{Fore.YELLOW}[!] WhisperX dependency missing: {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Install with: pip install whisperx{Style.RESET_ALL}")
                print(f"{Fore.GREEN}[*] Falling back to vanilla Whisper...{Style.RESET_ALL}\n")

            # Generic WhisperX error
            else:
                print(f"\n{Fore.YELLOW}[!] WhisperX error: {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}[*] Falling back to vanilla Whisper...{Style.RESET_ALL}\n")

            # Automatic fallback to vanilla Whisper
            try:
                print(f"{Fore.CYAN}[*] Using vanilla Whisper instead (no speaker diarization){Style.RESET_ALL}\n")
                return self._transcribe_vanilla(audio_path, language, podcast_mode)
            except Exception as fallback_error:
                raise Exception(f"Both WhisperX and Whisper failed. WhisperX: {str(e)}, Whisper: {str(fallback_error)}")

    def _transcribe_elevenlabs(self, audio_path: Path, language: Optional[str], podcast_mode: bool) -> Dict[str, any]:
        """Transcribe using ElevenLabs cloud API (synchronous)."""
        try:
            from elevenlabs.client import ElevenLabs

            if not self.elevenlabs_api_key:
                raise Exception("ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable.")

            print(f"[*] Initializing ElevenLabs client...")
            client = ElevenLabs(api_key=self.elevenlabs_api_key)

            # Check file size (max 3GB) and duration (max 10 hours)
            file_size = audio_path.stat().st_size
            file_size_gb = file_size / (1024**3)
            if file_size_gb > 3.0:
                raise Exception(f"File size ({file_size_gb:.2f} GB) exceeds ElevenLabs limit of 3GB. Use Whisper instead.")

            duration = self._get_audio_duration(str(audio_path))
            if duration > 36000:  # 10 hours
                raise Exception(f"Audio duration ({duration/3600:.1f} hours) exceeds ElevenLabs limit of 10 hours. Use Whisper instead.")

            # Upload and submit transcription job
            print(f"[*] Uploading and transcribing audio with ElevenLabs ({file_size_gb:.2f} GB)...")
            print(f"[*] Audio duration: {self._format_timestamp(duration)}")
            print(f"[*] This may take a few minutes...")
            print()

            # Open file and submit for transcription (synchronous)
            with open(audio_path, 'rb') as audio_file:
                # Using Speech to Text API with speaker diarization and audio events
                # Build parameters dict
                params = {
                    "model_id": "scribe_v2",  # Use latest V2 model
                    "file": audio_file,
                    "diarize": True,  # Enable speaker diarization
                    "diarization_threshold": 0.15,  # Lower = more sensitive to different voices (default: 0.22)
                    "tag_audio_events": True,  # Enable laughter, applause, etc.
                    "additional_formats": [{"format": "srt"}]  # Request SRT format (much more token-efficient than JSON)
                }
                # Note: diarization_threshold can only be set when num_speakers=None
                # Lower threshold = more speakers detected (higher chance of splitting one speaker into two)
                # Higher threshold = fewer speakers detected (higher chance of merging two speakers into one)

                # Only add language_code if explicitly provided (omit for auto-detect)
                if language:
                    params["language_code"] = language

                response = client.speech_to_text.convert(**params)

            print(f"[+] Transcription complete!")
            print()

            # Extract transcript data from response with speaker diarization
            plain_text = ""

            # Check for speaker diarization in additional_formats (SRT)
            if hasattr(response, 'additional_formats') and response.additional_formats:
                print(f"[*] Processing transcription with speaker diarization and audio events...")

                # additional_formats is a list of AdditionalFormatResponseModel objects
                # Find the SRT format in the list
                srt_format = None
                for fmt in response.additional_formats:
                    if hasattr(fmt, 'requested_format') and fmt.requested_format == 'srt':
                        srt_format = fmt
                        break

                # Parse SRT format for speaker labels, audio events, and timestamps
                if srt_format and hasattr(srt_format, 'content') and srt_format.content:
                    srt_content = srt_format.content

                    # Parse SRT format (token-efficient AND preserves timestamps for YouTube bookmarks)
                    # SRT format: subtitle blocks with timestamps and speaker labels
                    # Example:
                    # 1
                    # 00:00:00,000 --> 00:00:05,000
                    # [SPEAKER_01] Text here

                    transcript_lines = []
                    current_speaker = None
                    current_text = []
                    current_timestamp = None

                    # Split into subtitle blocks (separated by blank lines)
                    for block in srt_content.strip().split('\n\n'):
                        lines = block.strip().split('\n')
                        if len(lines) >= 3:
                            # lines[0] = subtitle number
                            # lines[1] = timestamp (e.g., "00:00:00,000 --> 00:00:05,000")
                            # lines[2+] = text (may include speaker label)

                            timestamp_line = lines[1]
                            text = ' '.join(lines[2:]).strip()

                            # Extract speaker if present (e.g., "[SPEAKER_01] text")
                            speaker = "SPEAKER_00"  # Default
                            if text.startswith('['):
                                # Check if it's a speaker label or audio event
                                end_bracket = text.find(']')
                                if end_bracket > 0:
                                    label = text[1:end_bracket]
                                    # SPEAKER_XX are speaker labels, others are audio events
                                    if label.startswith('SPEAKER_'):
                                        speaker = label
                                        text = text[end_bracket + 1:].strip()
                                    # Keep audio events like [laughter], [music] in the text

                            if not text:
                                continue

                            # Parse timestamp to get start time in seconds
                            # Format: "00:00:00,000 --> 00:00:05,000"
                            start_time = timestamp_line.split(' --> ')[0]
                            timestamp_seconds = self._parse_srt_timestamp(start_time)

                            # Group by speaker
                            if speaker != current_speaker:
                                # New speaker - save previous and start new
                                if current_text and current_timestamp is not None:
                                    # Format: **[SPEAKER_01]** `[00:12:34]` Text here...
                                    formatted_timestamp = self._format_timestamp(current_timestamp)
                                    transcript_lines.append(
                                        f"**[{current_speaker}]** `[{formatted_timestamp}]` {' '.join(current_text)}\n"
                                    )
                                current_speaker = speaker
                                current_text = [text]
                                current_timestamp = timestamp_seconds
                            else:
                                # Same speaker - continue
                                current_text.append(text)

                    # Add final segment
                    if current_text and current_timestamp is not None:
                        formatted_timestamp = self._format_timestamp(current_timestamp)
                        transcript_lines.append(
                            f"**[{current_speaker}]** `[{formatted_timestamp}]` {' '.join(current_text)}\n"
                        )

                    plain_text = '\n'.join(transcript_lines)
                    print(f"[+] Speaker diarization and timestamps extracted")
                    print(f"[*] Timestamps preserved for YouTube bookmarks")
                else:
                    # No SRT format, fall back to plain text
                    plain_text = response.text if hasattr(response, 'text') else ""
            else:
                # No additional_formats, use plain text
                plain_text = response.text if hasattr(response, 'text') else ""

            # Get language from response
            detected_language = response.language_code if hasattr(response, 'language_code') else "unknown"

            # Create markdown header with metadata
            markdown_content = f"""# Transcript

**Language:** {detected_language}
**Duration:** {self._format_timestamp(duration)}
**Transcription:** ElevenLabs (Speaker Diarization + Audio Events)

---

{plain_text}
"""

            # Save as Markdown file
            md_file = self.output_dir / f"{audio_path.stem}_transcript.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"[+] Detected language: {detected_language}")
            try:
                print(f"[*] Saved to: {md_file}")
            except UnicodeEncodeError:
                print(f"[*] Files saved to transcripts directory")

            return {
                'text': plain_text,
                'language': detected_language,
                'text_file': str(md_file)
            }

        except Exception as e:
            error_msg = str(e).lower()

            # Detect API key issues
            if 'api key' in error_msg or 'authentication' in error_msg or 'unauthorized' in error_msg:
                print(f"\n{Fore.YELLOW}{'='*70}")
                print(f"{Fore.YELLOW}[!] ElevenLabs Authentication Error{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}\n")
                print(f"{Fore.YELLOW}Problem: Invalid or missing ElevenLabs API key{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Error: {str(e)[:150]}{Style.RESET_ALL}\n")
                print(f"{Fore.CYAN}Solution:{Style.RESET_ALL}")
                print(f"{Fore.CYAN}1. Get your API key from: https://elevenlabs.io/app/speech-synthesis{Style.RESET_ALL}")
                print(f"{Fore.CYAN}2. Add to .env file: ELEVENLABS_API_KEY=your_key_here{Style.RESET_ALL}\n")

            # Detect quota/billing issues
            elif 'quota' in error_msg or 'limit' in error_msg or 'billing' in error_msg:
                print(f"\n{Fore.YELLOW}[!] ElevenLabs quota exceeded or billing issue{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Error: {str(e)[:150]}{Style.RESET_ALL}\n")
                print(f"{Fore.CYAN}Consider using Whisper/WhisperX for free local transcription{Style.RESET_ALL}\n")

            # Detect network issues
            elif 'connection' in error_msg or 'network' in error_msg or 'timeout' in error_msg:
                print(f"\n{Fore.YELLOW}[!] Network error: {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Check your internet connection and try again{Style.RESET_ALL}\n")

            # Detect import errors
            elif 'import' in error_msg or 'module' in error_msg:
                print(f"\n{Fore.YELLOW}[!] ElevenLabs SDK not installed: {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Install with: pip install elevenlabs{Style.RESET_ALL}\n")

            # Generic error
            else:
                print(f"\n{Fore.YELLOW}[!] ElevenLabs transcription error: {str(e)}{Style.RESET_ALL}\n")

            raise Exception(f"ElevenLabs transcription failed: {str(e)}")

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _parse_srt_timestamp(timestamp: str) -> float:
        """
        Parse SRT timestamp format to seconds.

        Args:
            timestamp: SRT timestamp in format "HH:MM:SS,mmm" (e.g., "00:01:23,456")

        Returns:
            Time in seconds as float
        """
        # Format: "00:01:23,456" -> 83.456 seconds
        try:
            time_part, ms_part = timestamp.split(',')
            hours, minutes, seconds = map(int, time_part.split(':'))
            milliseconds = int(ms_part)

            total_seconds = hours * 3600 + minutes * 60 + seconds + (milliseconds / 1000.0)
            return total_seconds
        except Exception:
            return 0.0
