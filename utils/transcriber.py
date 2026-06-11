"""
Audio Transcription Module
Transcribes audio files using OpenAI's Whisper or WhisperX with speaker diarization.
"""

import os
import sys
import time
import threading
import subprocess
import json
from pathlib import Path
from typing import Any, Dict, Optional
from colorama import Fore, Style


class AudioTranscriber:
    """Handles audio transcription using Whisper or WhisperX."""

    def __init__(self, model_name: str = "base", output_dir: str = "transcripts",
                 use_whisperx: bool = False, hf_token: Optional[str] = None,
                 use_elevenlabs: bool = False, elevenlabs_api_key: Optional[str] = None,
                 engine: Optional[str] = None, openai_api_key: Optional[str] = None,
                 num_speakers: Optional[int] = None):
        """
        Initialize the transcriber.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            output_dir: Directory to save transcripts
            use_whisperx: Legacy flag for the whisperx engine (prefer engine=)
            hf_token: Hugging Face token for speaker diarization (required if use_whisperx=True)
            use_elevenlabs: Legacy flag for the elevenlabs engine (prefer engine=)
            elevenlabs_api_key: ElevenLabs API key (required for elevenlabs engine)
            engine: Transcription engine: whisper, whisperx, parakeet, elevenlabs,
                    openai. Takes precedence over the legacy use_* flags.
            openai_api_key: OpenAI API key (required for openai engine)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._stop_progress = False
        # engine= is the modern selector; the use_* booleans remain so
        # pre-0.2.0 library callers keep working unchanged
        if engine is None:
            engine = "whisperx" if use_whisperx else "elevenlabs" if use_elevenlabs else "whisper"
        self.engine = engine
        self.use_whisperx = (engine == "whisperx")
        self.use_elevenlabs = (engine == "elevenlabs")
        self.model_name = model_name
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        # Optional hint for diarizing engines when the speaker count is known
        # upfront - constrains pyannote's clustering and improves accuracy
        self.num_speakers = num_speakers
        self._parakeet_model = None

        # Use custom Whisper cache location (defaults to ~/.cache/whisper)
        # Set WHISPER_CACHE_DIR to customize location
        default_cache = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
        whisper_cache = os.getenv("WHISPER_CACHE_DIR", default_cache)
        os.makedirs(whisper_cache, exist_ok=True)
        self.whisper_cache = whisper_cache

        if self.engine == "openai":
            print(f"[*] Using OpenAI gpt-4o-transcribe-diarize (cloud, speaker diarization)")
            if not self.openai_api_key:
                print(f"{Fore.YELLOW}[!] Warning: No OPENAI_API_KEY found - transcription will fail.{Style.RESET_ALL}")
            self.model = None  # No local model needed
        elif self.engine in ("parakeet", "parakeet-dia"):
            # NVIDIA Parakeet TDT 0.6B v3 via onnx-asr: pure-Python, no torch,
            # ~670MB int8 model downloaded to the HF cache on first use
            self._import_onnx_asr()  # fail fast with install hint if missing
            if self.engine == "parakeet-dia":
                # Diarized variant: pyannote segments speakers, parakeet
                # transcribes each turn
                try:
                    import pyannote.audio  # noqa: F401
                except ImportError as e:
                    raise ImportError(
                        "parakeet-dia requires pyannote.audio. Install with:\n"
                        "  uv sync --extra diarize\n"
                        "and set HF_TOKEN (accept terms on pyannote/speaker-diarization-3.1 "
                        "and pyannote/segmentation-3.0)."
                    ) from e
                if not self.hf_token:
                    print(f"{Fore.YELLOW}[!] Warning: No HF_TOKEN found - pyannote model download will fail.{Style.RESET_ALL}")
                print(f"[*] Using Parakeet + pyannote speaker diarization (local)")
            else:
                print(f"[*] Using NVIDIA Parakeet TDT 0.6B v3 (local, 25 languages)")
            print(f"[+] Parakeet initialized (model will load on first use)")
            self.model = None
        elif self.use_elevenlabs:
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
            # WhisperX models are loaded per-transcription for efficiency.
            # The vanilla Whisper fallback (used if WhisperX hits CUDA issues)
            # is loaded lazily too - eager loading doubled startup time and
            # memory for runs where WhisperX works fine.
            self._import_whisper()  # fail fast with install hint if missing
            print(f"[+] WhisperX initialized (model will load on first use)")
            self.model = None
        else:
            whisper = self._import_whisper()
            print(f"[*] Loading Whisper model: {model_name}")
            print(f"[*] Model cache: {whisper_cache}")
            self.model = whisper.load_model(model_name, download_root=whisper_cache)
            print(f"[+] Model loaded successfully")

    def _ensure_vanilla_model(self):
        """Load the vanilla Whisper model if it isn't loaded yet."""
        if self.model is None:
            whisper = self._import_whisper()
            print(f"[*] Loading Whisper model: {self.model_name}")
            print(f"[*] Model cache: {self.whisper_cache}")
            self.model = whisper.load_model(self.model_name, download_root=self.whisper_cache)
            print(f"[+] Model loaded successfully")
        return self.model

    @staticmethod
    def _import_whisper():
        """Import openai-whisper, raising an actionable error when the optional extra is missing."""
        try:
            import whisper
            return whisper
        except ImportError as e:
            raise ImportError(
                "Local transcription requires openai-whisper and PyTorch, which are optional extras.\n"
                "Install them with:\n"
                "  uv sync --extra whisper\n"
                "  (or: uv pip install openai-whisper torch torchaudio)\n"
                "Alternatively, use --transcription-engine elevenlabs for cloud transcription "
                "(no local models needed).\n"
                f"Original error: {e}"
            ) from e

    @staticmethod
    def _get_audio_duration(audio_file: str) -> float:
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
        except Exception:
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
                   podcast_mode: bool = True) -> Dict[str, Any]:
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
        if self.engine == "elevenlabs":
            return self._transcribe_elevenlabs(audio_path, language, podcast_mode)
        elif self.engine == "whisperx":
            return self._transcribe_whisperx(audio_path, language, podcast_mode)
        elif self.engine == "openai":
            return self._transcribe_openai(audio_path, language)
        elif self.engine == "parakeet":
            return self._transcribe_parakeet(audio_path, language)
        elif self.engine == "parakeet-dia":
            return self._transcribe_parakeet_dia(audio_path, language)
        else:
            return self._transcribe_vanilla(audio_path, language, podcast_mode)

    def _transcribe_vanilla(self, audio_path: Path, language: Optional[str], podcast_mode: bool) -> Dict[str, Any]:
        """Transcribe using vanilla Whisper."""
        try:
            model = self._ensure_vanilla_model()

            # Get audio duration for progress estimation
            duration = self._get_audio_duration(str(audio_path))

            # Start progress bar in separate thread
            self._stop_progress = False
            progress_thread = None
            if duration > 0:
                progress_thread = threading.Thread(target=self._show_progress, args=(duration,))
                progress_thread.daemon = True
                progress_thread.start()

            # Style prompt for conversational content. Kept topic-neutral:
            # naming subjects here (e.g. "technology podcast") biases Whisper
            # toward those words on unrelated content.
            if podcast_mode:
                initial_prompt = (
                    "This is a recording of people speaking naturally, with occasional filler words. "
                    "Use proper punctuation and capitalize names, places, organizations, and technical terms correctly. "
                    "Format in complete sentences with clear paragraph breaks. "
                    "Minimize excessive filler words like um, uh, you know."
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

            result = model.transcribe(
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

    def _transcribe_whisperx(self, audio_path: Path, language: Optional[str], podcast_mode: bool) -> Dict[str, Any]:
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

    def _transcribe_elevenlabs(self, audio_path: Path, language: Optional[str], podcast_mode: bool) -> Dict[str, Any]:
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
                    "diarization_threshold": 0.15,  # Balanced threshold (range: 0.1-0.4, default: 0.22)
                    "tag_audio_events": True,  # Enable laughter, applause, etc.
                    "additional_formats": [
                        {"format": "srt"},  # For timestamps
                        {"format": "segmented_json"}  # For speaker labels (SRT doesn't include them!)
                    ]
                }
                # Note: diarization_threshold can only be set when num_speakers=None
                # Lower threshold = more speakers detected (risk: may split one speaker into multiple)
                # Higher threshold = fewer speakers detected (risk: may merge different speakers into one)
                # Using 0.15 for balanced detection - reduces over-segmentation while still detecting genuine speakers

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
                # Find segmented_json (includes speaker labels AND timestamps)
                json_format = None
                for fmt in response.additional_formats:
                    if hasattr(fmt, 'requested_format') and fmt.requested_format == 'segmented_json':
                        json_format = fmt
                        break

                # Parse segmented_json for speaker labels, audio events, and timestamps
                if json_format and hasattr(json_format, 'content') and json_format.content:
                    import json as json_lib
                    json_data = json_lib.loads(json_format.content)

                    # Parse word-level data with speaker_id from segmented_json
                    # Structure: {"segments": [{"words": [{"text": "I", "start": 11.76, "speaker_id": "speaker_0", ...}]}]}
                    transcript_lines = []
                    current_speaker = None
                    current_words = []
                    current_start = None

                    # Extract words with speaker_id and timestamps
                    for segment in json_data.get('segments', []):
                        for word in segment.get('words', []):
                            word_type = word.get('type', 'word')
                            speaker = word.get('speaker_id', 'speaker_0')
                            word_text = word.get('text', '')
                            word_start = word.get('start', 0)

                            # Skip empty text but keep all types (words, spacing, punctuation, audio_events)
                            if not word_text:
                                continue

                            # New speaker detected (only on word/audio_event, not spacing)
                            if word_type in ['word', 'audio_event'] and speaker != current_speaker:
                                # Save previous segment
                                if current_words and current_start is not None:
                                    timestamp = self._format_timestamp(current_start)
                                    text = ''.join(current_words).strip()
                                    if text:  # Only add non-empty segments
                                        transcript_lines.append(
                                            f"**[{current_speaker.upper()}]** `[{timestamp}]` {text}\n"
                                        )
                                # Start new segment
                                current_speaker = speaker
                                current_words = [word_text]
                                current_start = word_start
                            else:
                                # Same speaker - continue (include ALL text: words, spacing, punctuation)
                                current_words.append(word_text)

                    # Add final segment
                    if current_words and current_start is not None:
                        timestamp = self._format_timestamp(current_start)
                        text = ''.join(current_words).strip()
                        if text:
                            transcript_lines.append(
                                f"**[{current_speaker.upper()}]** `[{timestamp}]` {text}\n"
                            )

                    plain_text = '\n'.join(transcript_lines)
                    print(f"[+] Speaker diarization and timestamps extracted from word-level data")
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

    # ------------------------------------------------------------------
    # OpenAI gpt-4o-transcribe-diarize (cloud, speaker diarization)
    # ------------------------------------------------------------------

    OPENAI_UPLOAD_LIMIT = 24 * 1024 * 1024  # API rejects files over 25MB

    def _prepare_for_openai(self, audio_path: Path) -> Path:
        """
        Ensure the upload fits the OpenAI 25MB file limit.

        Speech transcribes fine at low bitrates, so oversized files are
        re-encoded to 16kbps mono Opus (3h of audio ~ 21MB) instead of being
        chunked - chunking would break speaker-label continuity.
        """
        if audio_path.stat().st_size <= self.OPENAI_UPLOAD_LIMIT:
            return audio_path

        compact = audio_path.with_suffix('.openai.ogg')
        print(f"[*] Audio exceeds OpenAI's 25MB limit - re-encoding to 16kbps mono Opus...")
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', str(audio_path), '-ac', '1', '-c:a', 'libopus',
             '-b:a', '16k', '-application', 'voip', str(compact)],
            capture_output=True, text=True, timeout=1800,
        )
        if result.returncode != 0 or not compact.exists():
            raise Exception(f"ffmpeg re-encode failed: {result.stderr[-300:]}")
        if compact.stat().st_size > self.OPENAI_UPLOAD_LIMIT:
            raise Exception(
                "Audio still exceeds OpenAI's 25MB limit after re-encoding "
                "(over ~3.5 hours). Use whisper, parakeet or elevenlabs for this file."
            )
        return compact

    def _transcribe_openai(self, audio_path: Path, language: Optional[str]) -> Dict[str, Any]:
        """Transcribe using OpenAI gpt-4o-transcribe-diarize (cloud)."""
        try:
            from openai import OpenAI

            if not self.openai_api_key:
                raise Exception("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

            client = OpenAI(api_key=self.openai_api_key)
            upload_path = self._prepare_for_openai(audio_path)

            duration = self._get_audio_duration(str(audio_path))
            print(f"[*] Uploading and transcribing with gpt-4o-transcribe-diarize...")
            print(f"[*] Audio duration: {self._format_timestamp(duration)}")

            with open(upload_path, 'rb') as audio_file:
                params: Dict[str, Any] = {
                    "model": "gpt-4o-transcribe-diarize",
                    "file": audio_file,
                    # diarized_json is required to receive speaker annotations;
                    # chunking_strategy is mandatory for audio over 30 seconds
                    "response_format": "diarized_json",
                    "chunking_strategy": "auto",
                }
                if language:
                    params["language"] = language
                response = client.audio.transcriptions.create(**params)

            # Clean up the temporary re-encoded file
            if upload_path != audio_path:
                upload_path.unlink(missing_ok=True)

            # Normalize the SDK response to a dict regardless of SDK version
            if hasattr(response, 'model_dump'):
                data = response.model_dump()
            elif isinstance(response, dict):
                data = response
            else:
                data = json.loads(str(response))

            segments = data.get('segments') or []
            if segments:
                lines = []
                for seg in segments:
                    speaker = str(seg.get('speaker', 'SPEAKER')).upper()
                    timestamp = self._format_timestamp(float(seg.get('start', 0) or 0))
                    text = (seg.get('text') or '').strip()
                    if text:
                        lines.append(f"**[{speaker}]** `[{timestamp}]` {text}\n")
                plain_text = '\n'.join(lines)
            else:
                plain_text = (data.get('text') or '').strip()

            if not plain_text:
                raise Exception("OpenAI returned an empty transcript")

            markdown_content = f"""# Transcript

**Language:** {language or 'auto'}
**Duration:** {self._format_timestamp(duration)}
**Transcription:** OpenAI gpt-4o-transcribe-diarize (Speaker Diarization)

---

{plain_text}
"""
            md_file = self.output_dir / f"{audio_path.stem}_transcript.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"[+] Transcription complete")
            print(f"[*] Saved to: {md_file}")

            return {
                'text': plain_text,
                'language': language or 'auto',
                'text_file': str(md_file),
            }

        except Exception as e:
            raise Exception(f"OpenAI transcription failed: {str(e)}")

    # ------------------------------------------------------------------
    # NVIDIA Parakeet TDT 0.6B v3 via onnx-asr (local, no torch)
    # ------------------------------------------------------------------

    @staticmethod
    def _import_onnx_asr():
        """Import onnx-asr, raising an actionable error when the extra is missing."""
        try:
            import onnx_asr
            return onnx_asr
        except ImportError as e:
            raise ImportError(
                "The parakeet engine requires onnx-asr (lightweight, no PyTorch).\n"
                "Install it with:\n"
                "  uv sync --extra parakeet\n"
                "  (or: uv pip install \"onnx-asr[cpu,hub]\")\n"
                f"Original error: {e}"
            ) from e

    def _segment_to_wav(self, audio_path: Path, segment_seconds: int = 120) -> list:
        """Split audio into 16kHz mono WAV segments via ffmpeg (temp files)."""
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp(prefix="sonopsis_parakeet_"))
        pattern = tmp_dir / "chunk_%04d.wav"
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', str(audio_path), '-ac', '1', '-ar', '16000',
             '-f', 'segment', '-segment_time', str(segment_seconds), str(pattern)],
            capture_output=True, text=True, timeout=1800,
        )
        if result.returncode != 0:
            raise Exception(f"ffmpeg segmentation failed: {result.stderr[-300:]}")
        return sorted(tmp_dir.glob("chunk_*.wav"))

    def _ensure_parakeet_model(self):
        """Load the Parakeet ONNX model if not yet loaded."""
        if self._parakeet_model is None:
            onnx_asr = self._import_onnx_asr()
            print(f"[*] Loading Parakeet TDT 0.6B v3 (int8) - first run downloads ~670MB to the HF cache...")
            self._parakeet_model = onnx_asr.load_model(
                "nemo-parakeet-tdt-0.6b-v3", quantization="int8"
            )
            print(f"[+] Parakeet model loaded")
        return self._parakeet_model

    def _transcribe_parakeet_dia(self, audio_path: Path, language: Optional[str]) -> Dict[str, Any]:
        """
        Diarized local transcription: pyannote finds who-speaks-when, then
        Parakeet transcribes each speaker turn separately. Per-turn slicing
        avoids the word-to-speaker timestamp alignment problem entirely.
        """
        import tempfile
        from pyannote.audio import Pipeline

        model = self._ensure_parakeet_model()

        # pyannote and slicing both want a 16kHz mono WAV
        tmp_dir = Path(tempfile.mkdtemp(prefix="sonopsis_dia_"))
        wav16 = tmp_dir / "audio16k.wav"
        try:
            subprocess.run(
                ['ffmpeg', '-y', '-loglevel', 'error', '-i', str(audio_path),
                 '-ac', '1', '-ar', '16000', str(wav16)],
                check=True, timeout=1800,
            )

            print(f"[*] Running pyannote speaker diarization...")
            # pyannote 4.x: community-1 is the current pipeline (gated - accept
            # terms at hf.co/pyannote/speaker-diarization-community-1)
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-community-1", token=self.hf_token
            )
            # Feed an in-memory waveform: pyannote 4's file decoder (torchcodec)
            # is unreliable on Windows, and we already have a known-format
            # 16kHz mono PCM16 wav that stdlib `wave` can read
            import wave as wave_mod
            import numpy as np
            import torch
            with wave_mod.open(str(wav16), 'rb') as wf:
                pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
            waveform = torch.from_numpy(pcm.astype('float32') / 32768.0).unsqueeze(0)
            dia_kwargs = {}
            if self.num_speakers:
                dia_kwargs["num_speakers"] = self.num_speakers
                print(f"[*] Using known speaker count: {self.num_speakers}")
            output = pipeline({"waveform": waveform, "sample_rate": 16000}, **dia_kwargs)
            # pyannote 4.x wraps the annotation in DiarizeOutput; 3.x returns it directly
            diarization = getattr(output, 'speaker_diarization', output)

            # Merge adjacent same-speaker turns separated by short gaps
            turns = []
            for segment, _, speaker in diarization.itertracks(yield_label=True):
                if turns and turns[-1][2] == speaker and segment.start - turns[-1][1] < 0.8:
                    turns[-1] = (turns[-1][0], segment.end, speaker)
                else:
                    turns.append((segment.start, segment.end, speaker))
            print(f"[+] {len(turns)} speaker turns, "
                  f"{len({t[2] for t in turns})} speakers detected")

            # Transcribe each turn with Parakeet
            lines = []
            for i, (start, end, speaker) in enumerate(turns):
                clip = tmp_dir / f"turn_{i:03d}.wav"
                subprocess.run(
                    ['ffmpeg', '-y', '-loglevel', 'error', '-i', str(wav16),
                     '-ss', f"{start:.2f}", '-to', f"{end:.2f}", str(clip)],
                    check=True, timeout=300,
                )
                text = (model.recognize(str(clip)) or '').strip()
                clip.unlink()
                if text:
                    lines.append(
                        f"**[{speaker.upper()}]** `[{self._format_timestamp(start)}]` {text}\n"
                    )

            plain_text = '\n'.join(lines)
            if not plain_text:
                raise Exception("parakeet-dia produced an empty transcript")

            duration = self._get_audio_duration(str(audio_path))
            markdown_content = f"""# Transcript

**Language:** {language or 'auto'}
**Duration:** {self._format_timestamp(duration)}
**Transcription:** Parakeet TDT 0.6B v3 + pyannote 3.1 (Speaker Diarization)

---

{plain_text}
"""
            md_file = self.output_dir / f"{audio_path.stem}_transcript.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"[+] Transcription complete")
            print(f"[*] Saved to: {md_file}")

            return {
                'text': plain_text,
                'language': language or 'auto',
                'text_file': str(md_file),
                # (start, end, speaker) turns for downstream scoring (DER)
                'turns': turns,
            }

        except Exception as e:
            raise Exception(f"parakeet-dia transcription failed: {str(e)}")
        finally:
            for f in tmp_dir.glob("*"):
                f.unlink(missing_ok=True)
            try:
                tmp_dir.rmdir()
            except OSError:
                pass

    def _transcribe_parakeet(self, audio_path: Path, language: Optional[str]) -> Dict[str, Any]:
        """Transcribe using NVIDIA Parakeet TDT 0.6B v3 (local, int8 ONNX)."""
        chunks = []
        try:
            self._ensure_parakeet_model()

            duration = self._get_audio_duration(str(audio_path))
            print(f"[*] Audio duration: {self._format_timestamp(duration)}")

            # Segment via ffmpeg: deterministic memory use on multi-hour audio,
            # and onnx-asr expects 16kHz mono WAV input
            chunks = self._segment_to_wav(audio_path)
            print(f"[*] Transcribing {len(chunks)} segment(s)...")

            texts = []
            for i, chunk in enumerate(chunks, 1):
                text = self._parakeet_model.recognize(str(chunk))
                if text and text.strip():
                    texts.append(text.strip())
                sys.stdout.write(f"\r{Fore.CYAN}[{i}/{len(chunks)}] segments transcribed{Style.RESET_ALL}")
                sys.stdout.flush()
            print()

            plain_text = ' '.join(texts).strip()
            if not plain_text:
                raise Exception("Parakeet returned an empty transcript")

            markdown_content = f"""# Transcript

**Language:** {language or 'auto'}
**Duration:** {self._format_timestamp(duration)}
**Transcription:** NVIDIA Parakeet TDT 0.6B v3 (local)

---

{plain_text}
"""
            md_file = self.output_dir / f"{audio_path.stem}_transcript.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"[+] Transcription complete")
            print(f"[*] Saved to: {md_file}")

            return {
                'text': plain_text,
                'language': language or 'auto',
                'text_file': str(md_file),
            }

        except Exception as e:
            raise Exception(f"Parakeet transcription failed: {str(e)}")
        finally:
            # Remove temp WAV segments
            for chunk in chunks:
                try:
                    chunk.unlink()
                    chunk.parent.rmdir()
                except OSError:
                    pass

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
