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
from datetime import datetime


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
            print(f"    ├─ Using ElevenLabs cloud transcription")
            if not self.elevenlabs_api_key:
                print(f"{Fore.YELLOW}    ├─ Warning: No ELEVENLABS_API_KEY found.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}    └─ Transcription will fail without a valid API key.{Style.RESET_ALL}")
            self.model = None  # No local model needed for ElevenLabs
        elif use_whisperx:
            print(f"    ├─ Using WhisperX with speaker diarization")
            if not self.hf_token:
                print(f"{Fore.YELLOW}    ├─ Warning: No HF_TOKEN found. Speaker diarization will be disabled.{Style.RESET_ALL}")
            # WhisperX models are loaded per-transcription for efficiency
            print(f"    ├─ WhisperX initialized (model will load on first use)")

            # Load vanilla Whisper as fallback in case WhisperX fails (CUDA issues, etc.)
            print(f"    ├─ Loading vanilla Whisper as fallback: {model_name}")
            self.model = whisper.load_model(model_name, download_root=whisper_cache)
            print(f"    └─ Fallback model loaded")
        else:
            print(f"    ├─ Loading Whisper model: {model_name}")
            self.model = whisper.load_model(model_name, download_root=whisper_cache)
            print(f"    └─ Model loaded")

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
            print(f"    ├─ File: {audio_path.name}")
        except UnicodeEncodeError:
            # Fallback for console encoding issues
            print(f"    ├─ File: [audio file]")

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
            sys.stdout.write(f"\r{Fore.CYAN}    └─ Transcription complete ({result['language']}){' ' * 30}\n{Style.RESET_ALL}")
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

            print(f"    ├─ Using device: {device}")

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
            sys.stdout.write(f"\r{Fore.CYAN}    ├─ Base transcription complete{' ' * 30}\n{Style.RESET_ALL}")
            sys.stdout.flush()

            # Align whisper output
            print(f"    ├─ Aligning transcript...")
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

            # Perform speaker diarization if HF token is available
            if self.hf_token:
                print(f"    ├─ Performing speaker diarization...")
                from pyannote.audio import Pipeline
                diarize_model = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self.hf_token
                ).to(torch.device(device))
                diarize_segments = diarize_model(str(audio_path))
                result = whisperx.assign_word_speakers(diarize_segments, result)

            print(f"    └─ WhisperX complete ({result.get('language', 'unknown')})")
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

    def _save_transcription_job(self, video_id: str, transcription_id: str, metadata: Dict) -> None:
        """
        Save transcription job ID for resume capability.

        Args:
            video_id: YouTube video ID (e.g., "R8TqBrrqL4U")
            transcription_id: ElevenLabs transcription ID
            metadata: Additional job metadata (audio_path, submitted_at, etc.)
        """
        jobs_dir = Path(".transcription_jobs")
        jobs_dir.mkdir(exist_ok=True)

        job_file = jobs_dir / f"{video_id}.json"
        job_data = {
            "transcription_id": transcription_id,
            "video_id": video_id,
            "submitted_at": datetime.now().isoformat(),
            **metadata
        }

        with open(job_file, 'w') as f:
            json.dump(job_data, f, indent=2)

    def _load_transcription_job(self, video_id: str) -> Optional[Dict]:
        """
        Load existing transcription job if available.

        Args:
            video_id: YouTube video ID

        Returns:
            Job data dict if found, None otherwise
        """
        jobs_dir = Path(".transcription_jobs")
        job_file = jobs_dir / f"{video_id}.json"

        if job_file.exists():
            try:
                with open(job_file, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None

    def _delete_transcription_job(self, video_id: str) -> None:
        """
        Delete transcription job file after completion.

        Args:
            video_id: YouTube video ID
        """
        jobs_dir = Path(".transcription_jobs")
        job_file = jobs_dir / f"{video_id}.json"

        if job_file.exists():
            job_file.unlink()

    def _process_elevenlabs_result(self, response, audio_path: Path, duration: float) -> Dict[str, any]:
        """
        Process ElevenLabs transcription result (shared by sync and async).

        Args:
            response: ElevenLabs API response object
            audio_path: Path to audio file
            duration: Audio duration in seconds

        Returns:
            Dictionary containing transcription results
        """
        # Extract transcript data from response with speaker diarization
        plain_text = ""

        # Check for speaker diarization in additional_formats (SRT)
        if hasattr(response, 'additional_formats') and response.additional_formats:
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

        return {
            'text': plain_text,
            'language': detected_language,
            'text_file': str(md_file)
        }

    def _transcribe_elevenlabs(self, audio_path: Path, language: Optional[str], podcast_mode: bool) -> Dict[str, any]:
        """Transcribe using ElevenLabs cloud API with async polling."""
        try:
            from elevenlabs.client import ElevenLabs

            if not self.elevenlabs_api_key:
                raise Exception("ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable.")

            # Extract video ID from filename (format: YT_{VIDEO_ID}_Title.mp3)
            filename = audio_path.stem
            video_id = None
            if filename.startswith('YT_'):
                parts = filename.split('_')
                if len(parts) >= 2:
                    video_id = parts[1]

            print(f"    ├─ Initializing ElevenLabs client...")
            # Extended timeout for synchronous mode (up to 2 hours for very long transcriptions)
            client = ElevenLabs(api_key=self.elevenlabs_api_key, timeout=7200)

            # Check file size (max 3GB) and duration (max 10 hours)
            file_size = audio_path.stat().st_size
            file_size_gb = file_size / (1024**3)
            if file_size_gb > 3.0:
                raise Exception(f"File size ({file_size_gb:.2f} GB) exceeds ElevenLabs limit of 3GB. Use Whisper instead.")

            duration = self._get_audio_duration(str(audio_path))
            if duration > 36000:  # 10 hours
                raise Exception(f"Audio duration ({duration/3600:.1f} hours) exceeds ElevenLabs limit of 10 hours. Use Whisper instead.")

            transcription_id = None

            # Check for existing job first
            if video_id:
                existing_job = self._load_transcription_job(video_id)
                if existing_job:
                    transcription_id = existing_job.get('transcription_id')
                    print(f"{Fore.GREEN}    ├─ Found existing job: {transcription_id}{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}    └─ Resuming polling (no re-upload needed){Style.RESET_ALL}")
                    print()

            # Submit new async job if no existing job
            if not transcription_id:
                print(f"    ├─ Submitting to ElevenLabs ({file_size_gb:.2f} GB, {self._format_timestamp(duration)})")
                print(f"    ├─ Estimated time: ~{self._format_timestamp(duration * 0.15)} (15% of duration)")
                print()

                # Open file and submit for synchronous transcription with streaming
                with open(audio_path, 'rb') as audio_file:
                    # Using Speech to Text API with speaker diarization and audio events
                    params = {
                        "model_id": "scribe_v2",  # Use latest V2 model
                        "file": audio_file,
                        "diarize": True,  # Enable speaker diarization
                        "diarization_threshold": 0.15,  # Balanced threshold (range: 0.1-0.4, default: 0.22)
                        "tag_audio_events": True,  # Enable laughter, applause, etc.
                        "additional_formats": [
                            {"format": "srt"},  # For timestamps
                            {"format": "segmented_json"}  # For speaker labels
                        ]
                    }

                    # Only add language_code if explicitly provided (omit for auto-detect)
                    if language:
                        params["language_code"] = language

                    # Submit and wait for response (blocks until complete)
                    print(f"    ├─ Uploading and transcribing...")
                    print()

                    response = client.speech_to_text.convert(**params)

                print(f"{Fore.GREEN}    └─ ElevenLabs complete!{Style.RESET_ALL}")
                print()

                # Extract and save transcription_id for future reference
                if hasattr(response, 'transcription_id'):
                    transcription_id = response.transcription_id
                    if video_id:
                        metadata = {
                            "audio_path": str(audio_path),
                            "file_size_gb": file_size_gb,
                            "duration": duration,
                            "language": language,
                            "completed": True
                        }
                        self._save_transcription_job(video_id, transcription_id, metadata)

                # Process result using helper method
                final_result = self._process_elevenlabs_result(response, audio_path, duration)

                # Delete job file on success
                if video_id:
                    self._delete_transcription_job(video_id)

                return final_result
            else:
                # Existing job found - try to poll for it
                poll_interval = 10  # Check every 10 seconds
                max_wait = 7200  # 2 hours max
                elapsed = 0
                last_update = 0
                update_interval = 30  # Show progress update every 30 seconds

                print(f"[*] Polling for transcription completion...")
                print()

                while elapsed < max_wait:
                    try:
                        # Try to get transcript
                        result = client.speech_to_text.transcripts.get(transcription_id)

                        # Check if complete (has text attribute with content)
                        if hasattr(result, 'text') and result.text:
                            print(f"\r{Fore.GREEN}[+] Transcription complete after {self._format_timestamp(elapsed)}!{Style.RESET_ALL}")
                            print()

                            # Process result using helper method
                            final_result = self._process_elevenlabs_result(result, audio_path, duration)

                            # Delete job file on success
                            if video_id:
                                self._delete_transcription_job(video_id)

                            return final_result

                    except Exception as e:
                        error_str = str(e).lower()
                        # 404 or "not found" means still processing or doesn't exist
                        if '404' in error_str or 'not found' in error_str:
                            pass  # Still processing, continue polling
                        else:
                            # Unexpected error - re-raise
                            raise

                    # Show progress update periodically
                    if elapsed - last_update >= update_interval:
                        sys.stdout.write(f"\r{Fore.CYAN}[*] Waiting for transcription... {self._format_timestamp(elapsed)} elapsed{Style.RESET_ALL}")
                        sys.stdout.flush()
                        last_update = elapsed

                    time.sleep(poll_interval)
                    elapsed += poll_interval

                # Timeout - job ID is still saved for manual resume
                raise TimeoutError(f"Transcription not ready after {max_wait} seconds. Job ID {transcription_id} saved for resume.")

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
