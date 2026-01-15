"""
Test configuration loading.
"""

import pytest
import yaml


class TestConfigFile:
    """Test config.yaml structure and content."""

    def test_config_file_exists(self, config_file):
        """Test that config.yaml exists."""
        assert config_file.exists(), f"config.yaml not found at {config_file}"

    def test_config_file_valid_yaml(self, config_file):
        """Test that config.yaml is valid YAML."""
        content = config_file.read_text(encoding='utf-8')
        try:
            config = yaml.safe_load(content)
            assert config is not None, "config.yaml parsed to None"
        except yaml.YAMLError as e:
            pytest.fail(f"config.yaml is not valid YAML: {e}")

    def test_config_has_defaults_section(self, config_file):
        """Test that config.yaml has defaults section."""
        content = config_file.read_text(encoding='utf-8')
        config = yaml.safe_load(content)
        assert 'defaults' in config, "config.yaml missing 'defaults' section"

    def test_config_has_paths_section(self, config_file):
        """Test that config.yaml has paths section."""
        content = config_file.read_text(encoding='utf-8')
        config = yaml.safe_load(content)
        assert 'paths' in config, "config.yaml missing 'paths' section"

    def test_config_default_models(self, config_file):
        """Test that default models are specified."""
        content = config_file.read_text(encoding='utf-8')
        config = yaml.safe_load(content)
        defaults = config.get('defaults', {})

        assert 'summary_model' in defaults, "Missing default summary_model"
        assert 'whisper_model' in defaults, "Missing default whisper_model"

    def test_config_paths_valid(self, config_file):
        """Test that path configurations are valid strings."""
        content = config_file.read_text(encoding='utf-8')
        config = yaml.safe_load(content)
        paths = config.get('paths', {})

        assert 'downloads' in paths, "Missing downloads path"
        assert 'transcripts' in paths, "Missing transcripts path"
        assert 'summaries' in paths, "Missing summaries path"

        # Ensure paths are strings
        for key, value in paths.items():
            assert isinstance(value, str), f"Path '{key}' should be a string"
