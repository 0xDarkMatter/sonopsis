"""
Test that prose/ directory structure and files are correct.
"""

import pytest


class TestProseStructure:
    """Test prose directory structure."""

    def test_prose_directory_exists(self, prose_dir):
        """Test that prose/ directory exists."""
        assert prose_dir.exists(), f"prose/ directory not found at {prose_dir}"
        assert prose_dir.is_dir(), "prose/ is not a directory"

    def test_prompts_directory_exists(self, prose_dir):
        """Test that prose/prompts/ directory exists."""
        prompts_dir = prose_dir / "prompts"
        assert prompts_dir.exists(), "prose/prompts/ directory not found"
        assert prompts_dir.is_dir(), "prose/prompts/ is not a directory"

    def test_protocols_directory_exists(self, prose_dir):
        """Test that prose/protocols/ directory exists."""
        protocols_dir = prose_dir / "protocols"
        assert protocols_dir.exists(), "prose/protocols/ directory not found"
        assert protocols_dir.is_dir(), "prose/protocols/ is not a directory"


class TestProseFiles:
    """Test prose files exist and are readable."""

    def test_system_prompt_exists(self, prose_dir):
        """Test that system.md exists."""
        system_file = prose_dir / "prompts" / "system.md"
        assert system_file.exists(), f"system.md not found at {system_file}"

    def test_system_prompt_readable(self, prose_dir):
        """Test that system.md is readable and not empty."""
        system_file = prose_dir / "prompts" / "system.md"
        content = system_file.read_text(encoding='utf-8')
        assert len(content) > 0, "system.md is empty"

    def test_analysis_basic_exists(self, prose_dir):
        """Test that analysis_basic.md exists."""
        file = prose_dir / "prompts" / "analysis_basic.md"
        assert file.exists(), f"analysis_basic.md not found at {file}"

    def test_analysis_basic_readable(self, prose_dir):
        """Test that analysis_basic.md is readable and contains expected content."""
        file = prose_dir / "prompts" / "analysis_basic.md"
        content = file.read_text(encoding='utf-8')
        assert len(content) > 100, "analysis_basic.md seems too short"
        assert "{title}" in content, "analysis_basic.md missing {title} placeholder"
        assert "{transcript}" in content or "{video_id}" in content, \
            "analysis_basic.md missing expected placeholders"

    def test_analysis_advanced_exists(self, prose_dir):
        """Test that analysis_advanced.md exists."""
        file = prose_dir / "prompts" / "analysis_advanced.md"
        assert file.exists(), f"analysis_advanced.md not found at {file}"

    def test_analysis_advanced_readable(self, prose_dir):
        """Test that analysis_advanced.md is readable and contains expected content."""
        file = prose_dir / "prompts" / "analysis_advanced.md"
        content = file.read_text(encoding='utf-8')
        assert len(content) > 100, "analysis_advanced.md seems too short"
        assert "{title}" in content, "analysis_advanced.md missing {title} placeholder"

    def test_speaker_identification_exists(self, prose_dir):
        """Test that speaker_identification.md exists."""
        file = prose_dir / "protocols" / "speaker_identification.md"
        assert file.exists(), f"speaker_identification.md not found at {file}"

    def test_speaker_identification_readable(self, prose_dir):
        """Test that speaker_identification.md is readable."""
        file = prose_dir / "protocols" / "speaker_identification.md"
        content = file.read_text(encoding='utf-8')
        assert len(content) > 50, "speaker_identification.md seems too short"
        assert "SPEAKER" in content, "speaker_identification.md missing SPEAKER reference"
