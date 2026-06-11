"""
Tests for the config.yaml loader (utils/config.py).
"""

from utils.config import DEFAULTS, load_config


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path):
        config = load_config(tmp_path / "nope.yaml")
        assert config == DEFAULTS
        assert config is not DEFAULTS  # must be a copy, not the shared dict

    def test_project_config_loads(self):
        """The repo's own config.yaml parses and merges cleanly."""
        config = load_config()
        assert config['defaults']['whisper_model'] in ("tiny", "base", "small", "medium", "large")
        assert config['paths']['summaries']

    def test_partial_override_merges_deeply(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("defaults:\n  whisper_model: large\n", encoding="utf-8")
        config = load_config(cfg)
        assert config['defaults']['whisper_model'] == "large"
        # untouched keys keep their defaults
        assert config['defaults']['analysis_mode'] == "basic"
        assert config['paths']['downloads'] == "downloads"

    def test_broken_yaml_falls_back_to_defaults(self, tmp_path, capsys):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("defaults: [unclosed", encoding="utf-8")
        config = load_config(cfg)
        assert config['defaults']['whisper_model'] == DEFAULTS['defaults']['whisper_model']
        assert "Warning" in capsys.readouterr().out

    def test_non_dict_yaml_ignored(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("- just\n- a\n- list\n", encoding="utf-8")
        config = load_config(cfg)
        assert config == DEFAULTS

    def test_defaults_not_mutated_across_loads(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("paths:\n  downloads: elsewhere\n", encoding="utf-8")
        load_config(cfg)
        assert DEFAULTS['paths']['downloads'] == "downloads"
