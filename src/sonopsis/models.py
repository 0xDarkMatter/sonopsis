"""
Model Registry
Single source of truth for summarization models: IDs, display info, and limits.

Menus, CLI help, and the summarizer all read from this registry so model
additions/renames happen in exactly one place.
"""

import os
from typing import Any, Dict, List, Optional

# Default model when an Anthropic API key is available (no Claude Code CLI)
DEFAULT_API_MODEL = "claude-sonnet-4-6"
# Default when the Claude Code CLI is installed (subscription billing)
DEFAULT_CLI_MODEL = "claude-cli"

# Approximate per-3-hour-video costs shown in menus. max_tokens is the model's
# maximum output capacity (Anthropic models reject values above it).
MODELS: Dict[str, Dict[str, Any]] = {
    # --- Claude Code CLI (subscription, no API key) ---
    "claude-cli": {
        "label": "Claude Code (Max plan)",
        "provider": "claude-cli",
        "cost": "$0 (subscription)",
        "speed": "Medium",
        "quality": "Best",
        "desc": "Uses your Claude subscription via the Claude Code CLI - no API key or per-token cost",
    },
    # --- Anthropic API ---
    "claude-sonnet-4-6": {
        "label": "Claude Sonnet 4.6",
        "provider": "anthropic",
        "cost": "~$0.25",
        "speed": "Medium",
        "quality": "Best",
        "desc": "Top quality: best speed/intelligence balance, excellent analysis",
        "max_tokens": 64000,
    },
    "claude-haiku-4-5-20251001": {
        "label": "Claude Haiku 4.5",
        "provider": "anthropic",
        "cost": "~$0.08",
        "speed": "Very Fast",
        "quality": "Excellent",
        "desc": "Best value: near-Sonnet quality at a third of the cost",
        "max_tokens": 64000,
    },
    "claude-opus-4-8": {
        "label": "Claude Opus 4.8",
        "provider": "anthropic",
        "cost": "~$0.80",
        "speed": "Slow",
        "quality": "Frontier",
        "desc": "Most capable Claude - premium choice for dense or technical content",
        "max_tokens": 128000,
        # Opus 4.7+ rejects the temperature parameter entirely
        "supports_temperature": False,
    },
    # Legacy alias kept for backwards compatibility with existing configs
    "claude-sonnet-4-5-20250929": {
        "label": "Claude Sonnet 4.5 (legacy)",
        "provider": "anthropic",
        "cost": "~$0.25",
        "speed": "Medium",
        "quality": "Great",
        "desc": "Previous-generation Sonnet - prefer claude-sonnet-4-6",
        "max_tokens": 64000,
        "hidden": True,  # accepted but not offered in menus
    },
    # --- OpenAI API ---
    "gpt-4o-mini": {
        "label": "GPT-4o-mini",
        "provider": "openai",
        "cost": "~$0.05",
        "speed": "Fastest",
        "quality": "Good",
        "desc": "Budget-friendly, great for simple summaries and quick overviews",
    },
    "gpt-4o": {
        "label": "GPT-4o",
        "provider": "openai",
        "cost": "~$0.15",
        "speed": "Fast",
        "quality": "Great",
        "desc": "Balanced model, good analysis and structured summaries",
    },
    "gpt-5.1": {
        "label": "GPT-5.1",
        "provider": "openai",
        "cost": "~$0.30",
        "speed": "Slow",
        "quality": "Excellent",
        "desc": "Latest OpenAI reasoning model, catches transcript errors",
    },
    # --- OpenRouter (OpenAI-compatible API) ---
    "openrouter/moonshot/kimi-k2": {
        "label": "Kimi K2 (OpenRouter)",
        "provider": "openrouter",
        "cost": "~$0.25",
        "speed": "Medium",
        "quality": "Great",
        "desc": "Long-context specialist (200K+), good for multi-hour transcripts",
    },
    "openrouter/zhipuai/glm-4.6-plus": {
        "label": "GLM 4.6 Plus (OpenRouter)",
        "provider": "openrouter",
        "cost": "~$0.15",
        "speed": "Medium",
        "quality": "Great",
        "desc": "Excellent multilingual support, especially Chinese content",
    },
}

PROVIDER_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def get_model_info(model: str) -> Optional[Dict[str, Any]]:
    """Look up a model in the registry. claude-cli/<alias> maps to claude-cli."""
    if model.startswith("claude-cli"):
        return MODELS.get("claude-cli")
    return MODELS.get(model)


def get_max_tokens(model: str, default: int = 64000) -> int:
    """Maximum output tokens for a model (used for Anthropic API calls)."""
    info = get_model_info(model)
    if info and "max_tokens" in info:
        return info["max_tokens"]
    return default


def available_models(claude_cli: bool = False) -> List[str]:
    """
    Models usable in the current environment, in menu order.

    Args:
        claude_cli: Whether the Claude Code CLI is installed
    """
    result = []
    for model_id, info in MODELS.items():
        if info.get("hidden"):
            continue
        provider = info["provider"]
        if provider == "claude-cli":
            if claude_cli:
                result.append(model_id)
        elif os.getenv(PROVIDER_ENV_KEYS[provider]):
            result.append(model_id)
    return result
