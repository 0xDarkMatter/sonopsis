"""
Content Summarization Module
Generates well-formatted summaries and notes using OpenAI's GPT models or Anthropic's Claude models.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from openai import OpenAI
from datetime import datetime

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

    def summarize(self, transcript: str, video_metadata: Dict[str, any],
                  analysis_mode: str = "advanced", transcription_engine: str = "whisper") -> Dict[str, str]:
        """
        Generate a comprehensive summary and notes from a transcript.

        Args:
            transcript: Video transcript text
            video_metadata: Dictionary containing video information
            analysis_mode: "basic" or "advanced" (default: "advanced")
            transcription_engine: Engine used for transcription (whisper, whisperx, elevenlabs)

        Returns:
            Dictionary containing summary, key points, and notes
        """
        print(f"[*] Generating summary using {self.model} ({analysis_mode} mode)")

        # Store transcription engine for metadata
        self.transcription_engine = transcription_engine

        # Load system prompt from external file
        system_prompt = self._load_system_prompt()

        # Create the prompt
        prompt = self._create_summary_prompt(transcript, video_metadata, analysis_mode)

        try:
            # Call appropriate API based on model type
            if self.api_type == 'anthropic':
                # Claude requires max_tokens parameter - use model maximum
                # Sonnet 4.5 supports up to 64K output tokens
                # Use streaming to avoid 10-minute timeout for long generations
                print(f"[*] Generating (this may take several minutes for long videos)...")

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
                    "temperature": 0.7
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

                response = self.client.chat.completions.create(**completion_params)
                summary_content = response.choices[0].message.content

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

            print(f"[+] Summary generated successfully")
            print(f"[*] Saved to: {output_file}")

            return {
                'summary': summary_content,
                'formatted_output': formatted_output,
                'output_file': str(output_file)
            }

        except Exception as e:
            raise Exception(f"Summarization failed: {str(e)}")

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

        # Replace placeholders
        prompt = template.format(
            title=metadata.get('title', 'Unknown'),
            uploader=metadata.get('uploader', 'Unknown'),
            duration=self._format_duration(metadata.get('duration', 0)),
            url=url,
            video_id=video_id,
            transcript=transcript
        )

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

        # Section 4: Video Description (if available)
        description = metadata.get('description', '')
        if description:
            header_parts.append("### Video Description")
            header_parts.append(description)
            header_parts.append("")

        # Section 5: Processing Information
        header_parts.append("### Processing Information")
        header_parts.append(f"**Transcription Model:** {transcription_display}")
        header_parts.append(f"**Summarization Model:** {summary_display}")
        header_parts.append(f"**Summary Mode:** {mode_display}")
        header_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
