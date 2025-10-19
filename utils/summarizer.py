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
                   - OpenAI: gpt-4o-mini, gpt-4o, gpt-5
                   - Anthropic: claude-sonnet-4-5-20250929, claude-haiku-4-5-20251001, claude-sonnet-4, claude-opus-4-1
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
        else:
            self.api_type = 'openai'
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            self.client = OpenAI(api_key=self.api_key)

    def summarize(self, transcript: str, video_metadata: Dict[str, any],
                  analysis_mode: str = "advanced") -> Dict[str, str]:
        """
        Generate a comprehensive summary and notes from a transcript.

        Args:
            transcript: Video transcript text
            video_metadata: Dictionary containing video information
            analysis_mode: "basic" or "advanced" (default: "advanced")

        Returns:
            Dictionary containing summary, key points, and notes
        """
        print(f"[*] Generating summary using {self.model} ({analysis_mode} mode)")

        # Create the prompt
        prompt = self._create_summary_prompt(transcript, video_metadata, analysis_mode)

        try:
            # Call appropriate API based on model type
            if self.api_type == 'anthropic':
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    temperature=0.7,
                    system="You are an expert at analyzing video and podcast content, creating comprehensive, well-structured summaries and notes. You excel at identifying speakers, capturing conversational nuances, extracting key insights, and organizing information clearly. You notice tone, emphasis, and the flow of discussions.",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                summary_content = response.content[0].text
            else:
                # OpenAI API
                # GPT-5 uses max_completion_tokens instead of max_tokens
                completion_params = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert at analyzing video and podcast content, creating comprehensive, well-structured summaries and notes. You excel at identifying speakers, capturing conversational nuances, extracting key insights, and organizing information clearly. You notice tone, emphasis, and the flow of discussions."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7
                }

                # GPT-5 and reasoning models have different parameter requirements
                if self.model.startswith('gpt-5') or self.model.startswith('o1') or self.model.startswith('o3'):
                    # GPT-5 requires max_completion_tokens and temperature=1 (default only)
                    completion_params["max_completion_tokens"] = 4000
                    completion_params["temperature"] = 1  # GPT-5 only supports default temperature
                else:
                    completion_params["max_tokens"] = 2000

                response = self.client.chat.completions.create(**completion_params)
                summary_content = response.choices[0].message.content

            # Generate formatted output
            formatted_output = self._format_output(summary_content, video_metadata)

            # Save to file
            output_file = self.output_dir / f"{self._sanitize_filename(video_metadata['title'])}_summary.md"
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

        # Replace placeholders
        prompt = template.format(
            title=metadata.get('title', 'Unknown'),
            uploader=metadata.get('uploader', 'Unknown'),
            duration=self._format_duration(metadata.get('duration', 0)),
            transcript=transcript
        )

        return prompt

    def _format_output(self, summary: str, metadata: Dict[str, any]) -> str:
        """Format the final output with metadata header."""
        header = f"""# Video Summary: {metadata.get('title', 'Unknown')}

---

**Channel:** {metadata.get('uploader', 'Unknown')}
**Duration:** {self._format_duration(metadata.get('duration', 0))}
**URL:** {metadata.get('url', 'N/A')}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
        return header + summary

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
    def _sanitize_filename(filename: str) -> str:
        """Remove invalid characters from filename."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        return filename[:200]  # Limit length
