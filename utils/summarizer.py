"""
Content Summarization Module
Generates well-formatted summaries and notes using OpenAI's GPT models or Anthropic's Claude models.
"""

import os
import re
import json
import time
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from openai import OpenAI
from datetime import datetime

from utils.models import get_max_tokens

# Transient API failures (rate limits, overload, network blips) are retried
# with exponential backoff. The transcript feeding a summary can represent
# 20+ minutes of transcription work - one 529 should not throw that away.
MAX_API_ATTEMPTS = 3
RETRY_BASE_DELAY = 5.0  # seconds

_TRANSIENT_ERROR_NAMES = {
    "RateLimitError", "APIConnectionError", "APITimeoutError",
    "InternalServerError", "OverloadedError", "ServiceUnavailableError",
}


def _is_transient(error: Exception) -> bool:
    """Whether an API error is worth retrying (rate limit, 5xx, network)."""
    if type(error).__name__ in _TRANSIENT_ERROR_NAMES:
        return True
    status = getattr(error, "status_code", None)
    return status is not None and (status == 429 or status >= 500)

# Try to import Anthropic, but make it optional
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def claude_cli_available() -> bool:
    """Check whether the Claude Code CLI is installed and on PATH."""
    return shutil.which("claude") is not None


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
                   - Claude Code CLI (subscription, no API key): claude-cli,
                     claude-cli/sonnet, claude-cli/opus, claude-cli/haiku
            output_dir: Directory to save summaries
        """
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Determine which API to use based on model name
        if model.startswith('claude-cli'):
            # Headless Claude Code - billed to the user's subscription (Pro/Max),
            # not an API key, so no key check needed.
            self.api_type = 'claude-cli'
            self.cli_path = shutil.which("claude")
            if not self.cli_path:
                raise ValueError(
                    "Claude Code CLI not found on PATH. Install it from "
                    "https://claude.com/claude-code or choose an API model instead."
                )
            # Optional model alias after a slash: claude-cli/sonnet -> sonnet
            self.cli_model = model.split('/', 1)[1] if '/' in model else None
            self.api_key = None
            self.client = None
        elif model.startswith('claude'):
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

    def summarize(self, transcript: str, video_metadata: Dict[str, Any],
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
            summary_content = self._generate_with_retry(system_prompt, prompt)

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

    def _generate_with_retry(self, system_prompt: str, prompt: str) -> str:
        """Run generation, retrying transient API failures with backoff."""
        last_error = None
        for attempt in range(1, MAX_API_ATTEMPTS + 1):
            try:
                return self._generate_once(system_prompt, prompt)
            except Exception as e:
                last_error = e
                if attempt == MAX_API_ATTEMPTS or not _is_transient(e):
                    raise
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                print(f"[!] Transient API error ({type(e).__name__}); "
                      f"retry {attempt}/{MAX_API_ATTEMPTS - 1} in {delay:.0f}s...")
                time.sleep(delay)
        raise last_error or RuntimeError("Summary generation failed")  # unreachable

    def _generate_once(self, system_prompt: str, prompt: str) -> str:
        """Single generation attempt against the configured backend."""
        if self.api_type == 'claude-cli':
            print(f"[*] Generating via Claude Code CLI (subscription, no API cost)...")
            return self._summarize_with_claude_cli(system_prompt, prompt)

        if self.api_type == 'anthropic':
            # Claude requires max_tokens - use the model's maximum from the
            # registry. Streaming avoids the 10-minute HTTP timeout on long
            # generations. No temperature: newer Opus models reject the
            # parameter entirely, and the default works well for summaries.
            print(f"[*] Generating (this may take several minutes for long videos)...")

            summary_content = ""
            with self.client.messages.stream(
                model=self.model,
                max_tokens=get_max_tokens(self.model),
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
            return summary_content

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

        # For OpenAI models, max_tokens is optional - if omitted, the model
        # uses its full output capacity. Reasoning models require
        # max_completion_tokens and temperature=1.
        if self.model.startswith('o1') or self.model.startswith('o3'):
            completion_params["max_completion_tokens"] = 32768
            completion_params["temperature"] = 1

        response = self.client.chat.completions.create(**completion_params)
        return response.choices[0].message.content

    def _summarize_with_claude_cli(self, system_prompt: str, prompt: str) -> str:
        """
        Generate a summary via the Claude Code CLI in headless mode.

        Uses the user's Claude subscription (Pro/Max) instead of API billing.
        The full payload goes through stdin: transcripts routinely exceed the
        Windows ~32K command-line limit, and long arguments through the npm
        .cmd shim are mangled by cmd.exe quoting rules.
        """
        cmd = [
            self.cli_path,
            '-p', 'You will receive a system prompt followed by a task. '
                  'Follow them exactly and output only the requested summary markdown.',
            '--output-format', 'json',
            '--disallowedTools', 'Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch,Task',
        ]
        if self.cli_model:
            cmd += ['--model', self.cli_model]

        payload = f"<system>\n{system_prompt}\n</system>\n\n{prompt}"

        try:
            result = subprocess.run(
                cmd,
                input=payload,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=3600,
            )
        except FileNotFoundError:
            raise Exception("Claude Code CLI not found. Install from https://claude.com/claude-code")
        except subprocess.TimeoutExpired:
            raise Exception("Claude Code CLI timed out after 60 minutes")

        if result.returncode != 0:
            stderr_snippet = (result.stderr or result.stdout or '').strip()[:300]
            raise Exception(f"Claude Code CLI failed (exit {result.returncode}): {stderr_snippet}")

        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise Exception(f"Claude Code CLI returned unparseable output: {result.stdout[:300]}")

        if response.get('is_error'):
            raise Exception(f"Claude Code CLI error: {response.get('result', 'unknown error')[:300]}")

        summary = response.get('result', '')
        if not summary or not summary.strip():
            raise Exception("Claude Code CLI returned an empty summary")

        return summary

    def _load_system_prompt(self) -> str:
        """
        Load the system prompt from external file.

        Returns:
            System prompt string
        """
        system_prompt_file = Path(__file__).parent.parent / "prose" / "prompts" / "system.md"

        if not system_prompt_file.exists():
            raise FileNotFoundError(f"System prompt file not found: {system_prompt_file}")

        # Load system prompt from file
        with open(system_prompt_file, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def _identify_speakers(self, transcript: str, metadata: Dict[str, Any]) -> str:
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

    def _create_summary_prompt(self, transcript: str, metadata: Dict[str, Any],
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
        prompt_file = Path(__file__).parent.parent / "prose" / "prompts" / f"analysis_{analysis_mode}.md"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Analysis prompt file not found: {prompt_file}")

        # Load prompt template from file
        with open(prompt_file, 'r', encoding='utf-8') as f:
            template = f.read()

        # Extract video ID from URL
        url = metadata.get('url', 'N/A')
        video_id = self._extract_video_id(url) or 'N/A'

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

    def _format_output(self, summary: str, metadata: Dict[str, Any]) -> str:
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
    def _extract_video_id(url: str) -> Optional[str]:
        """
        Extract YouTube video ID from URL.

        Returns None when no ID is found - never a placeholder string, since
        the ID is embedded in output filenames ('N/A' would inject a slash).
        """
        patterns = [
            r'(?:youtube\.com/watch\?(?:[^#]*&)?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/(?:embed|v|shorts|live)/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

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
