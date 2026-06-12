"""
Tests for the model registry (src/sonopsis/models.py).
"""

from unittest.mock import patch

from sonopsis.models import (
    MODELS, PROVIDER_ENV_KEYS,
    available_models, get_max_tokens, get_model_info,
)


class TestRegistryIntegrity:
    def test_every_model_has_required_fields(self):
        for model_id, info in MODELS.items():
            for field in ("label", "provider", "cost", "speed", "quality", "desc"):
                assert field in info, f"{model_id} missing {field}"

    def test_providers_are_known(self):
        known = set(PROVIDER_ENV_KEYS) | {"claude-cli"}
        for model_id, info in MODELS.items():
            assert info["provider"] in known, f"{model_id} has unknown provider"

    def test_anthropic_models_declare_max_tokens(self):
        """Anthropic API calls require an explicit max_tokens ceiling."""
        for model_id, info in MODELS.items():
            if info["provider"] == "anthropic":
                assert "max_tokens" in info, f"{model_id} missing max_tokens"


class TestLookups:
    def test_get_model_info_cli_alias(self):
        assert get_model_info("claude-cli/opus") == MODELS["claude-cli"]

    def test_get_model_info_unknown(self):
        assert get_model_info("some-future-model") is None

    def test_get_max_tokens_known(self):
        assert get_max_tokens("claude-opus-4-8") == 128000

    def test_get_max_tokens_unknown_uses_default(self):
        assert get_max_tokens("some-future-model") == 64000
        assert get_max_tokens("some-future-model", default=1234) == 1234


class TestAvailableModels:
    def test_no_backends(self, monkeypatch):
        for key in PROVIDER_ENV_KEYS.values():
            monkeypatch.delenv(key, raising=False)
        assert available_models(claude_cli=False) == []

    def test_claude_cli_only(self, monkeypatch):
        for key in PROVIDER_ENV_KEYS.values():
            monkeypatch.delenv(key, raising=False)
        assert available_models(claude_cli=True) == ["claude-cli"]

    def test_anthropic_key_exposes_claude_models(self, monkeypatch):
        for key in PROVIDER_ENV_KEYS.values():
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        models = available_models(claude_cli=False)
        assert "claude-sonnet-4-6" in models
        assert all(MODELS[m]["provider"] == "anthropic" for m in models)

    def test_hidden_models_excluded(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        assert "claude-sonnet-4-5-20250929" not in available_models()
