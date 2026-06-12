"""
Edge-case tests for the credential store (src/sonopsis/credentials.py).
Keyring access is mocked throughout - no OS keyring is touched.
"""

import pytest
from unittest.mock import patch

from sonopsis import credentials
from sonopsis.credentials import (
    PROVIDERS, CredentialStore, auth_overview, export_to_env, get_credential,
)


class TestProviderValidation:
    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            CredentialStore("not-a-provider")

    def test_all_declared_providers_construct(self):
        for provider in PROVIDERS:
            assert CredentialStore(provider).env_var


class TestResolutionOrder:
    def test_env_wins_over_keyring(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "from-env")
        with patch.object(credentials, "keyring") as kr:
            kr.get_password.return_value = "from-keyring"
            store = CredentialStore("openai")
            assert store.get() == "from-env"
            assert store.get_source() == "env"

    def test_keyring_used_when_env_missing(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.object(credentials, "keyring") as kr:
            kr.get_password.return_value = "from-keyring"
            store = CredentialStore("openai")
            assert store.get() == "from-keyring"
            assert store.get_source() == "keyring"

    def test_nothing_configured(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.object(credentials, "keyring") as kr:
            kr.get_password.return_value = None
            store = CredentialStore("openai")
            assert store.get() is None
            assert store.get_source() is None


class TestNoKeyringBackend:
    """Headless systems: keyring import failed entirely."""

    def test_get_falls_back_to_env_only(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.object(credentials, "KEYRING_AVAILABLE", False):
            assert CredentialStore("openai").get() is None

    def test_set_raises_actionable_error(self):
        with patch.object(credentials, "KEYRING_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                CredentialStore("openai").set("x")

    def test_delete_returns_false(self):
        with patch.object(credentials, "KEYRING_AVAILABLE", False):
            assert CredentialStore("openai").delete() is False

    def test_keyring_exceptions_swallowed(self, monkeypatch):
        """A broken keyring backend must never crash credential lookup."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.object(credentials, "keyring") as kr:
            kr.get_password.side_effect = RuntimeError("dbus exploded")
            assert CredentialStore("openai").get() is None
            assert CredentialStore("openai").get_source() is None


class TestExportToEnv:
    def test_backfills_only_missing_vars(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "already-set")
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        with patch.object(credentials, "keyring") as kr:
            kr.get_password.side_effect = (
                lambda service, provider: "kr-value" if provider == "elevenlabs" else None
            )
            export_to_env()
        import os
        assert os.environ["OPENAI_API_KEY"] == "already-set"  # untouched
        assert os.environ["ELEVENLABS_API_KEY"] == "kr-value"  # backfilled
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)


class TestDelete:
    def test_delete_removes_existing_credential(self):
        with patch.object(credentials, "keyring") as kr:
            kr.get_password.return_value = "stored"
            assert CredentialStore("openai").delete() is True
            kr.delete_password.assert_called_once_with("sonopsis", "openai")

    def test_delete_nothing_stored_returns_false(self):
        with patch.object(credentials, "keyring") as kr:
            kr.get_password.return_value = None
            assert CredentialStore("openai").delete() is False
            kr.delete_password.assert_not_called()

    def test_delete_swallows_keyring_errors(self):
        with patch.object(credentials, "keyring") as kr:
            kr.get_password.side_effect = RuntimeError("locked")
            assert CredentialStore("openai").delete() is False


class TestConvenience:
    def test_get_credential_matches_store(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "abc")
        assert get_credential("openai") == "abc"


class TestAuthOverview:
    def test_overview_covers_all_providers_plus_cli(self):
        overview = auth_overview()
        assert set(PROVIDERS) <= set(overview)
        assert "claude-cli" in overview
        for row in overview.values():
            assert "configured" in row and "unlocks" in row

    def test_claude_cli_detected_via_path(self):
        with patch("shutil.which", return_value=r"C:\fake\claude.exe"):
            row = auth_overview()["claude-cli"]
        assert row["configured"] is True
        assert row["source"] == "PATH"

    def test_claude_cli_absent(self):
        with patch("shutil.which", return_value=None):
            row = auth_overview()["claude-cli"]
        assert row["configured"] is False
        assert row["source"] is None
