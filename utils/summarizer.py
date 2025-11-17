"""
Content Summarization Module
Generates well-formatted summaries and notes using OpenAI's GPT models or Anthropic's Claude models.
"""

import os
import sys
import time
import threading
import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from openai import OpenAI
from datetime import datetime
from colorama import Fore, Style
import tiktoken

# Try to import Anthropic, but make it optional
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class ContentSummarizer:
    """Handles content summarization and note generation using GPT or Claude."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", output_dir: str = "summaries"):
        """
        Initialize the summarizer.

        Args:
            api_key: API key (if None, reads from environment based on model)
            model: Model to use. Options:
                   - OpenAI: gpt-4o-mini, gpt-4o, gpt-5.1
                   - Anthropic: claude-sonnet-4-5-20250929, claude-haiku-4-5-20251001, claude-sonnet-4, claude-opus-4-1
                   - OpenRouter: openrouter/moonshot/kimi-k2, openrouter/zhipuai/glm-4.6-plus
            output_dir: Directory to save summaries
        """
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._stop_progress = False
        self._char_count = 0

        # Token counting setup
        try:
            # Try to get encoding for the specific model
            if model.startswith('gpt'):
                self.encoding = tiktoken.encoding_for_model(model)
            elif model.startswith('claude'):
                # Claude uses cl100k_base encoding (same as GPT-4)
                self.encoding = tiktoken.get_encoding("cl100k_base")
            else:
                # Fallback to cl100k_base for other models
                self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback encoding if model not recognized
            self.encoding = tiktoken.get_encoding("cl100k_base")

        # Determine model-specific token limits
        self._set_model_token_limits(model)

        # Determine which API to use based on model name
        if model.startswith('claude'):
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic package not installed. Run: pip install anthropic")
            self.api_type = 'anthropic'
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
            self.client = Anthropic(api_key=self.api_key)
        elif model.startswith('openrouter/'):
            # OpenRouter uses OpenAI-compatible API
            self.api_type = 'openrouter'
            self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
            if not self.api_key:
                raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
            # Strip the openrouter/ prefix for the actual API call
            self.model = model.replace('openrouter/', '', 1)
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/yourusername/sonopsis",  # Optional, for rankings
                    "X-Title": "Sonopsis"  # Optional, shows in OpenRouter rankings
                }
            )
        else:
            self.api_type = 'openai'
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            self.client = OpenAI(api_key=self.api_key)

    def _set_model_token_limits(self, model: str):
        """
        Set model-specific token limits for chunking strategy.

        Different models have different context windows:
        - Claude Sonnet 4.5: 200K input
        - Claude Haiku 4.5: 200K input
        - GPT-4o: 128K input
        - GPT-4o-mini: 128K input
        - GPT-5: 128K input
        - Gemini 1.5/2.0: 1-2M input (via OpenRouter)

        Args:
            model: Model name
        """
        # Define model context windows (input tokens)
        model_limits = {
            # Claude models
            'claude-sonnet-4-5': 200000,
            'claude-haiku-4-5': 200000,
            'claude-opus-4': 200000,
            'claude-sonnet-4': 200000,

            # OpenAI models
            'gpt-4o': 128000,
            'gpt-4o-mini': 128000,
            'gpt-5': 128000,
            'o1': 200000,
            'o3': 200000,

            # Gemini via OpenRouter
            'gemini-1.5-pro': 2000000,
            'gemini-1.5-flash': 1000000,
            'gemini-2.0-flash': 1000000,
            'google/gemini': 1000000,  # OpenRouter prefix

            # Other OpenRouter models
            'kimi-k2': 128000,
            'glm-4': 128000,
        }

        # Find matching limit
        context_window = 128000  # Default fallback
        for model_key, limit in model_limits.items():
            if model_key in model.lower():
                context_window = limit
                break

        # Set conservative limits (75% of context window to leave room for output and overhead)
        self.max_input_tokens = int(context_window * 0.75)

        # Set chunk target based on context window
        # For very large windows (>500K), use bigger chunks
        if context_window >= 500000:
            self.chunk_target_tokens = 100000  # Gemini can handle larger chunks
        else:
            self.chunk_target_tokens = 40000  # Standard chunk size

        # Store for logging
        self.context_window = context_window

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # Fallback: rough estimate (1 token ≈ 0.75 words)
            return int(len(text.split()) * 1.3)

    def _chunk_transcript(self, transcript: str, metadata: Dict) -> List[Tuple[str, int, int]]:
        """
        Intelligently chunk transcript by speaker segments and timestamps.

        Args:
            transcript: Full transcript text
            metadata: Video metadata

        Returns:
            List of tuples: (chunk_text, start_line, end_line)
        """
        # Split transcript into segments (by speaker/timestamp)
        lines = transcript.split('\n')

        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_start_line = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Count tokens for this line
            line_tokens = self._count_tokens(line)

            # Check if adding this line would exceed target
            if current_tokens + line_tokens > self.chunk_target_tokens and current_chunk:
                # Save current chunk
                chunk_text = '\n'.join(current_chunk)
                chunks.append((chunk_text, chunk_start_line, i - 1))

                # Start new chunk
                current_chunk = [line]
                current_tokens = line_tokens
                chunk_start_line = i
            else:
                # Add to current chunk
                current_chunk.append(line)
                current_tokens += line_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append((chunk_text, chunk_start_line, len(lines) - 1))

        return chunks

    def _show_streaming_progress(self):
        """Show streaming progress indicator with character count."""
        start_time = time.time()
        print()  # Add space above

        while not self._stop_progress:
            elapsed = time.time() - start_time
            elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"

            # Create animated dots
            dots = "." * ((int(elapsed * 2) % 3) + 1) + " " * (3 - ((int(elapsed * 2) % 3) + 1))

            # Show progress with character count
            progress_text = f"\r{Fore.CYAN}    ├─ Generating{dots} {elapsed_str} | {self._char_count:,} chars generated{Style.RESET_ALL}"
            try:
                sys.stdout.write(progress_text)
                sys.stdout.flush()
            except UnicodeEncodeError:
                pass

            time.sleep(0.5)

    def summarize(self, transcript: str, video_metadata: Dict[str, any],
                  analysis_mode: str = "advanced", transcription_engine: str = "whisper") -> Dict[str, str]:
        """
        Generate a comprehensive summary and notes from a transcript.
        Automatically uses chunking for long transcripts.

        Args:
            transcript: Video transcript text
            video_metadata: Dictionary containing video information
            analysis_mode: "basic" or "advanced" (default: "advanced")
            transcription_engine: Engine used for transcription (whisper, whisperx, elevenlabs)

        Returns:
            Dictionary containing summary, key points, and notes
        """
        # Store transcription engine for metadata
        self.transcription_engine = transcription_engine

        # Count tokens in transcript + estimated overhead
        transcript_tokens = self._count_tokens(transcript)
        system_prompt = self._load_system_prompt()
        system_tokens = self._count_tokens(system_prompt)
        metadata_str = str(video_metadata)
        metadata_tokens = self._count_tokens(metadata_str)

        total_input_tokens = transcript_tokens + system_tokens + metadata_tokens + 1000  # +1000 for prompt template

        print(f"    ├─ Using {self.model} ({analysis_mode} mode)")
        print(f"    ├─ Model context window: {self.context_window:,} tokens")
        print(f"    ├─ Transcript: {transcript_tokens:,} tokens")

        # Decide whether to use chunking
        if total_input_tokens > self.max_input_tokens:
            print(f"    ├─ Total input ({total_input_tokens:,} tokens) exceeds safe limit ({self.max_input_tokens:,})")
            print(f"    ├─ Using chunked summarization (chunk size: {self.chunk_target_tokens:,} tokens)")
            return self._summarize_chunked(transcript, video_metadata, analysis_mode)
        else:
            utilization = (total_input_tokens / self.max_input_tokens) * 100
            print(f"    ├─ Total input: {total_input_tokens:,} tokens ({utilization:.1f}% of limit)")
            return self._summarize_single(transcript, video_metadata, analysis_mode)

    def _summarize_single(self, transcript: str, video_metadata: Dict[str, any], analysis_mode: str) -> Dict[str, str]:
        """
        Generate summary from a single transcript (no chunking needed).

        Args:
            transcript: Video transcript text
            video_metadata: Dictionary containing video information
            analysis_mode: "basic" or "advanced"

        Returns:
            Dictionary containing summary, key points, and notes
        """
        # Load system prompt from external file
        system_prompt = self._load_system_prompt()

        # Create the prompt
        prompt = self._create_summary_prompt(transcript, video_metadata, analysis_mode)

        try:
            # Start progress indicator
            self._stop_progress = False
            self._char_count = 0
            progress_thread = threading.Thread(target=self._show_streaming_progress)
            progress_thread.daemon = True
            progress_thread.start()

            # Call appropriate API based on model type
            if self.api_type == 'anthropic':
                # Claude requires max_tokens parameter - use model maximum
                # Sonnet 4.5 supports up to 64K output tokens
                # Use streaming to avoid 10-minute timeout for long generations
                summary_content = ""
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=64000,  # Claude Sonnet 4.5 maximum output capacity
                    temperature=0.7,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                ) as stream:
                    for text in stream.text_stream:
                        summary_content += text
                        self._char_count = len(summary_content)
            else:
                # OpenAI API (also used by OpenRouter with compatible interface)
                completion_params = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "stream": True  # Enable streaming for progress
                }

                # For OpenAI models, max_tokens is optional
                # If omitted, model uses its full output capacity
                # Only set for reasoning models that require it
                if self.model.startswith('o1') or self.model.startswith('o3'):
                    # Reasoning models require max_completion_tokens and temperature=1
                    completion_params["max_completion_tokens"] = 32768  # o1 supports up to 100k
                    completion_params["temperature"] = 1
                # For GPT-4o, GPT-5, and OpenRouter models: don't limit output tokens
                # Let the model use its full capacity

                summary_content = ""
                stream = self.client.chat.completions.create(**completion_params)
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        summary_content += chunk.choices[0].delta.content
                        self._char_count = len(summary_content)

            # Stop progress indicator
            self._stop_progress = True
            progress_thread.join(timeout=1)

            # Clear the line and show completion
            sys.stdout.write(f"\r{Fore.CYAN}    └─ Generated {len(summary_content):,} characters{' ' * 30}\n{Style.RESET_ALL}")
            sys.stdout.flush()
            print()

            # Generate formatted output
            formatted_output = self._format_output(summary_content, video_metadata)

            # Extract video ID and create filename with YT_{ID}_ prefix
            video_id = self._extract_video_id(video_metadata.get('url', ''))
            if video_id:
                filename = f"YT_{video_id}_{self._sanitize_filename(video_metadata['title'])}_summary.md"
            else:
                # Fallback to old naming if ID extraction fails
                filename = f"{self._sanitize_filename(video_metadata['title'])}_summary.md"

            # Save to file
            output_file = self.output_dir / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_output)

            return {
                'summary': summary_content,
                'formatted_output': formatted_output,
                'output_file': str(output_file)
            }

        except Exception as e:
            raise Exception(f"Summarization failed: {str(e)}")

    def _summarize_chunked(self, transcript: str, video_metadata: Dict[str, any], analysis_mode: str) -> Dict[str, str]:
        """
        Generate summary using map-reduce strategy for long transcripts.

        Strategy:
        1. MAP: Split transcript into chunks and summarize each
        2. REDUCE: Combine chunk summaries into final comprehensive summary

        Args:
            transcript: Video transcript text
            video_metadata: Dictionary containing video information
            analysis_mode: "basic" or "advanced"

        Returns:
            Dictionary containing summary, key points, and notes
        """
        try:
            # Step 1: Chunk the transcript
            chunks = self._chunk_transcript(transcript, video_metadata)
            num_chunks = len(chunks)

            print(f"    ├─ Split into {num_chunks} chunks for processing")
            print()

            # Step 2: MAP - Summarize each chunk
            chunk_summaries = []

            for idx, (chunk_text, start_line, end_line) in enumerate(chunks, 1):
                print(f"    ├─ Processing chunk {idx}/{num_chunks} (lines {start_line}-{end_line})")

                # Create chunk-specific prompt
                chunk_prompt = self._create_chunk_summary_prompt(chunk_text, idx, num_chunks, video_metadata, analysis_mode)
                system_prompt = "You are an expert at analyzing and summarizing video transcripts. Focus on extracting key insights, quotes, and important details from this segment."

                # Start progress indicator for this chunk
                self._stop_progress = False
                self._char_count = 0
                progress_thread = threading.Thread(target=self._show_streaming_progress)
                progress_thread.daemon = True
                progress_thread.start()

                # Summarize chunk
                chunk_summary = ""
                if self.api_type == 'anthropic':
                    with self.client.messages.stream(
                        model=self.model,
                        max_tokens=16000,  # Smaller output for chunks
                        temperature=0.7,
                        system=system_prompt,
                        messages=[{"role": "user", "content": chunk_prompt}]
                    ) as stream:
                        for text in stream.text_stream:
                            chunk_summary += text
                            self._char_count = len(chunk_summary)
                else:
                    stream = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": chunk_prompt}
                        ],
                        temperature=0.7,
                        stream=True
                    )
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            chunk_summary += chunk.choices[0].delta.content
                            self._char_count = len(chunk_summary)

                # Stop progress
                self._stop_progress = True
                progress_thread.join(timeout=1)

                chunk_summaries.append(chunk_summary)
                print(f"\r{Fore.CYAN}    │  └─ Chunk {idx}/{num_chunks} complete ({len(chunk_summary):,} chars){' ' * 20}{Style.RESET_ALL}")
                print()

            # Step 3: REDUCE - Combine chunk summaries into final summary
            print(f"    ├─ Combining {num_chunks} chunk summaries into final summary")

            combined_prompt = self._create_reduce_summary_prompt(chunk_summaries, video_metadata, analysis_mode)
            system_prompt = self._load_system_prompt()

            # Start progress indicator for final summary
            self._stop_progress = False
            self._char_count = 0
            progress_thread = threading.Thread(target=self._show_streaming_progress)
            progress_thread.daemon = True
            progress_thread.start()

            # Generate final summary
            summary_content = ""
            if self.api_type == 'anthropic':
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=64000,
                    temperature=0.7,
                    system=system_prompt,
                    messages=[{"role": "user", "content": combined_prompt}]
                ) as stream:
                    for text in stream.text_stream:
                        summary_content += text
                        self._char_count = len(summary_content)
            else:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": combined_prompt}
                    ],
                    temperature=0.7,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        summary_content += chunk.choices[0].delta.content
                        self._char_count = len(summary_content)

            # Stop progress
            self._stop_progress = True
            progress_thread.join(timeout=1)

            sys.stdout.write(f"\r{Fore.CYAN}    └─ Generated {len(summary_content):,} characters{' ' * 30}\n{Style.RESET_ALL}")
            sys.stdout.flush()
            print()

            # Generate formatted output
            formatted_output = self._format_output(summary_content, video_metadata)

            # Extract video ID and create filename
            video_id = self._extract_video_id(video_metadata.get('url', ''))
            if video_id:
                filename = f"YT_{video_id}_{self._sanitize_filename(video_metadata['title'])}_summary.md"
            else:
                filename = f"{self._sanitize_filename(video_metadata['title'])}_summary.md"

            # Save to file
            output_file = self.output_dir / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_output)

            return {
                'summary': summary_content,
                'formatted_output': formatted_output,
                'output_file': str(output_file)
            }

        except Exception as e:
            raise Exception(f"Chunked summarization failed: {str(e)}")

    def _create_chunk_summary_prompt(self, chunk_text: str, chunk_num: int, total_chunks: int,
                                     metadata: Dict, analysis_mode: str) -> str:
        """Create prompt for summarizing a single chunk."""
        return f"""This is segment {chunk_num} of {total_chunks} from a video titled: "{metadata.get('title', 'Unknown')}"

Please extract and summarize the key information from this segment:
- Main topics and themes discussed
- Important quotes or statements
- Key insights and takeaways
- Any technical details or specific information

Keep your summary focused and detailed. This will be combined with other segments later.

TRANSCRIPT SEGMENT:
{chunk_text}
"""

    def _create_reduce_summary_prompt(self, chunk_summaries: List[str], metadata: Dict, analysis_mode: str) -> str:
        """Create prompt for combining chunk summaries into final summary."""
        combined_summaries = "\n\n---\n\n".join([f"SEGMENT {i+1} SUMMARY:\n{summary}" for i, summary in enumerate(chunk_summaries)])

        return f"""I have provided summaries of {len(chunk_summaries)} segments from a video titled: "{metadata.get('title', 'Unknown')}"

Please create a comprehensive, well-structured final summary by combining these segment summaries.

Your task:
1. Synthesize all segment summaries into a cohesive narrative
2. Identify overarching themes and key topics
3. Extract the most important quotes and insights
4. Organize information logically (not just chronologically)
5. Create a summary following the {analysis_mode} analysis format

SEGMENT SUMMARIES:
{combined_summaries}

Now create the comprehensive final summary following the standard format for {analysis_mode} mode.
"""

    def _load_system_prompt(self) -> str:
        """
        Load the system prompt from external file.

        Returns:
            System prompt string
        """
        system_prompt_file = Path(__file__).parent.parent / "docs" / "system_prompt.md"

        if not system_prompt_file.exists():
            raise FileNotFoundError(f"System prompt file not found: {system_prompt_file}")

        # Load system prompt from file
        with open(system_prompt_file, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def _identify_speakers(self, transcript: str, metadata: Dict[str, any]) -> str:
        """
        Analyze transcript and metadata to identify speakers.

        Args:
            transcript: Full transcript with SPEAKER_X labels
            metadata: Video metadata including title, description

        Returns:
            Speaker mapping guidance string to inject into prompt
        """
        import re

        # Extract first 3000 characters of transcript for analysis
        transcript_sample = transcript[:3000]

        # Find all unique SPEAKER_X labels
        speakers = set(re.findall(r'\*\*\[SPEAKER_(\d+)\]', transcript_sample))

        if not speakers:
            return ""

        # Build analysis prompt
        mapping_prompt = "\n\n**SPEAKER MAPPING ASSISTANCE:**\n\n"
        mapping_prompt += f"The transcript contains {len(speakers)} speakers: " + ", ".join(f"SPEAKER_{s}" for s in sorted(speakers)) + "\n\n"

        # Add metadata clues
        title = metadata.get('title', '')
        description = metadata.get('description', '')
        uploader = metadata.get('uploader', '')

        if title:
            mapping_prompt += f"**Video Title:** {title}\n"
        if uploader:
            mapping_prompt += f"**Channel:** {uploader}\n"

        # Extract name clues from title and description
        if description:
            # Look for common patterns: "with X and Y", "X speaks with Y", etc.
            name_patterns = [
                r'with ([A-Z][a-z]+ [A-Z][a-z]+) and ([A-Z][a-z]+ [A-Z][a-z]+)',
                r'([A-Z][a-z]+ [A-Z][a-z]+) and ([A-Z][a-z]+ [A-Z][a-z]+)',
                r'featuring ([A-Z][a-z]+ [A-Z][a-z]+)',
            ]

            for pattern in name_patterns:
                matches = re.findall(pattern, description[:500])
                if matches:
                    mapping_prompt += f"\n**Names mentioned in description:** {', '.join(sum(matches, ()) if isinstance(matches[0], tuple) else matches)}\n"
                    break

        # Show first few speaker segments
        mapping_prompt += "\n**First speaker segments for analysis:**\n"
        segments = re.findall(r'\*\*\[(SPEAKER_\d+)\]\*\*.{0,150}', transcript_sample)
        for i, segment in enumerate(segments[:15], 1):
            mapping_prompt += f"{i}. {segment}...\n"

        mapping_prompt += "\n**Use this information to map SPEAKER_X labels to actual names in your summary.**\n"

        return mapping_prompt

    def _create_summary_prompt(self, transcript: str, metadata: Dict[str, any],
                               analysis_mode: str = "advanced") -> str:
        """
        Create the prompt for GPT by loading from external file.

        Args:
            transcript: Transcript text
            metadata: Video metadata
            analysis_mode: "basic" or "advanced"

        Returns:
            Formatted prompt string
        """
        # Determine prompt file path
        prompt_file = Path(__file__).parent.parent / "docs" / f"analysis_{analysis_mode}.md"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Analysis prompt file not found: {prompt_file}")

        # Load prompt template from file
        with open(prompt_file, 'r', encoding='utf-8') as f:
            template = f.read()

        # Extract video ID from URL
        url = metadata.get('url', 'N/A')
        video_id = self._extract_video_id(url) if url != 'N/A' else 'N/A'

        # Generate speaker mapping assistance
        speaker_mapping = self._identify_speakers(transcript, metadata)

        # Replace placeholders
        prompt = template.format(
            title=metadata.get('title', 'Unknown'),
            uploader=metadata.get('uploader', 'Unknown'),
            duration=self._format_duration(metadata.get('duration', 0)),
            url=url,
            video_id=video_id,
            transcript=transcript
        )

        # Append speaker mapping guidance
        if speaker_mapping:
            prompt = prompt + speaker_mapping

        return prompt

    def _format_output(self, summary: str, metadata: Dict[str, any]) -> str:
        """Format the final output with metadata header."""
        # Format transcription model display name
        transcription_display = self._get_transcription_display_name(
            self.transcription_engine,
            metadata.get('whisper_model', 'base')
        )

        # Format summarization model display name
        if self.api_type == 'anthropic':
            summary_display = f"Anthropic {self.model}"
        elif self.api_type == 'openrouter':
            summary_display = f"OpenRouter: {self.model}"
        else:
            summary_display = f"OpenAI {self.model}"

        # Format analysis mode
        analysis_mode = metadata.get('analysis_mode', 'advanced')
        mode_display = "Advanced (Narrative)" if analysis_mode == "advanced" else "Basic (Structured)"

        # Format upload date (YYYYMMDD -> YYYY-MM-DD)
        upload_date = metadata.get('upload_date', 'Unknown')
        if upload_date != 'Unknown' and len(upload_date) == 8:
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        # Build sectioned header
        header_parts = [f"# Video Summary: {metadata.get('title', 'Unknown')}", ""]
        header_parts.append("---")
        header_parts.append("")

        # Section 1: Video Information
        header_parts.append("### Video Information")
        header_parts.append(f"**Channel:** {metadata.get('uploader', 'Unknown')}")

        channel_url = metadata.get('channel_url', '')
        if channel_url:
            header_parts.append(f"**Channel URL:** {channel_url}")

        header_parts.append(f"**Published:** {upload_date}")
        header_parts.append(f"**Duration:** {self._format_duration(metadata.get('duration', 0))}")

        language = metadata.get('language', '')
        if language:
            header_parts.append(f"**Language:** {language}")

        header_parts.append(f"**URL:** {metadata.get('url', 'N/A')}")
        header_parts.append("")

        # Section 2: Engagement Metrics
        view_count = metadata.get('view_count', 0)
        like_count = metadata.get('like_count', 0)
        if view_count > 0 or like_count > 0:
            header_parts.append("### Engagement Metrics")
            if view_count > 0:
                header_parts.append(f"**Views:** {self._format_number(view_count)}")
            if like_count > 0:
                header_parts.append(f"**Likes:** {self._format_number(like_count)}")
            header_parts.append("")

        # Section 3: Content Details
        tags = metadata.get('tags', [])
        categories = metadata.get('categories', [])
        chapters = metadata.get('chapters', [])

        if tags or categories or chapters:
            header_parts.append("### Content Details")

            if tags:
                tags_str = ', '.join(tags[:20])  # Limit to first 20 tags
                if len(tags) > 20:
                    tags_str += f" (+{len(tags) - 20} more)"
                header_parts.append(f"**Tags:** {tags_str}")

            if categories:
                header_parts.append(f"**Categories:** {', '.join(categories)}")

            if chapters:
                header_parts.append(f"**Chapters:** {len(chapters)} detected")
                for i, chapter in enumerate(chapters, 1):
                    start_time = self._format_timestamp_from_seconds(chapter.get('start_time', 0))
                    title = chapter.get('title', f'Chapter {i}')
                    header_parts.append(f"  - `{start_time}` {title}")

            header_parts.append("")

        # Section 4: Processing Information
        header_parts.append("### Processing Information")
        header_parts.append(f"**Transcription Model:** {transcription_display}")
        header_parts.append(f"**Summarization Model:** {summary_display}")
        header_parts.append(f"**Summary Mode:** {mode_display}")
        header_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        header_parts.append("")

        # Section 5: Video Description (if available) - placed last as it can be very long
        description = metadata.get('description', '')
        if description:
            header_parts.append("### Video Description")
            header_parts.append(description)
            header_parts.append("")

        header_parts.append("---")
        header_parts.append("")

        return "\n".join(header_parts) + summary

    @staticmethod
    def _get_transcription_display_name(engine: str, whisper_model: str = "base") -> str:
        """Get display name for transcription engine."""
        engine_names = {
            "whisper": f"Whisper ({whisper_model})",
            "whisperx": "WhisperX (with speaker diarization)",
            "elevenlabs": "ElevenLabs Scribe V2"
        }
        return engine_names.get(engine, engine)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format duration in seconds to HH:MM:SS."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    @staticmethod
    def _format_timestamp_from_seconds(seconds: float) -> str:
        """Format seconds to HH:MM:SS timestamp."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_number(num: int) -> str:
        """Format large numbers with commas (e.g., 1234567 -> 1,234,567)."""
        return f"{num:,}"

    @staticmethod
    def _extract_video_id(url: str) -> str:
        """Extract YouTube video ID from URL."""
        try:
            # Handle different YouTube URL formats
            if 'youtu.be/' in url:
                # Format: https://youtu.be/VIDEO_ID
                return url.split('youtu.be/')[-1].split('?')[0]
            elif 'watch?v=' in url:
                # Format: https://www.youtube.com/watch?v=VIDEO_ID
                return url.split('watch?v=')[-1].split('&')[0]
            else:
                return 'N/A'
        except:
            return 'N/A'

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Remove invalid characters from filename and normalize Unicode.

        Converts curly quotes, em dashes, and other Unicode to ASCII equivalents.
        """
        # First, normalize common Unicode characters to ASCII
        unicode_replacements = {
            '\u2018': "'",  # Left single quote
            '\u2019': "'",  # Right single quote
            '\u201c': '"',  # Left double quote
            '\u201d': '"',  # Right double quote
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
            '\u2026': '...',  # Ellipsis
            '\u00a0': ' ',  # Non-breaking space
        }

        for unicode_char, ascii_char in unicode_replacements.items():
            filename = filename.replace(unicode_char, ascii_char)

        # Remove invalid filesystem characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')

        # Remove any remaining non-ASCII characters
        filename = ''.join(char if ord(char) < 128 else '' for char in filename)

        # Clean up multiple spaces
        filename = ' '.join(filename.split())

        return filename[:200]  # Limit length
