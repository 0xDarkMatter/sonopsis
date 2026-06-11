"""
Configuration Loader
Reads config.yaml (non-secret settings) and merges it over built-in defaults.

Precedence (lowest to highest): built-in defaults < config.yaml < env vars < CLI flags.
API keys never live here - they come from .env / the environment.
"""

import copy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

CONFIG_FILENAME = "config.yaml"

DEFAULTS: Dict[str, Any] = {
    "defaults": {
        "summary_model": None,  # None = auto-select (claude-cli if installed, else API default)
        "whisper_model": "base",
        "transcription_engine": None,  # None = auto-select (parakeet if installed, else whisper)
        "analysis_mode": "basic",
    },
    "paths": {
        "downloads": "downloads",
        "transcripts": "transcripts",
        "summaries": "summaries",
    },
    "whisper": {
        "device": "auto",
    },
    "processing": {
        "keep_files": False,
        "cleanup_partials": True,
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge override into base recursively. Override wins on conflicts."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def default_engine(configured: Optional[str] = None) -> str:
    """
    Resolve the default transcription engine.

    Benchmarks (benchmarks/results.md) show Parakeet TDT v3 beats Whisper
    decisively on wideband audio (0% vs 3-20% WER on LibriSpeech), so it is
    preferred when its optional extra is installed. Whisper remains the
    fallback - and the better choice for narrowband/telephone audio.
    """
    if configured:
        return configured
    try:
        import onnx_asr  # noqa: F401
        return "parakeet"
    except ImportError:
        return "whisper"


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration, merging config.yaml over built-in defaults.

    Args:
        config_path: Explicit path to a config file. Defaults to config.yaml
                     next to the package root (the project directory).

    Returns:
        Full config dict - always contains every key from DEFAULTS.
    """
    config = copy.deepcopy(DEFAULTS)

    if config_path is None:
        config_path = Path(__file__).parent.parent / CONFIG_FILENAME

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
            if isinstance(user_config, dict):
                config = _deep_merge(config, user_config)
        except yaml.YAMLError as e:
            # A broken config file should not brick the tool - warn and continue
            print(f"[!] Warning: could not parse {config_path.name} ({e}); using defaults")

    return config
