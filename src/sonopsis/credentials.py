"""
Credential Store
Multi-provider credential management following agent-first CLI conventions.

Resolution order (first hit wins): environment variable > .env file (loaded
into the environment at startup) > OS keyring. Keys saved via `sonopsis auth
login` land in the OS keyring under the service name "sonopsis".
"""

import os
from typing import Optional

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:  # headless systems without a keyring backend
    KEYRING_AVAILABLE = False

SERVICE = "sonopsis"
KEYRING_SERVICE = "sonopsis"

# provider -> (env var, what it unlocks)
PROVIDERS = {
    "openai": ("OPENAI_API_KEY", "GPT summaries + gpt-4o-transcribe-diarize engine"),
    "anthropic": ("ANTHROPIC_API_KEY", "Claude API summaries (not needed for claude-cli)"),
    "openrouter": ("OPENROUTER_API_KEY", "Kimi/GLM summaries via OpenRouter"),
    "elevenlabs": ("ELEVENLABS_API_KEY", "ElevenLabs Scribe transcription"),
    "hf": ("HF_TOKEN", "pyannote speaker diarization (parakeet-dia, WhisperX)"),
}


class CredentialStore:
    """Get/set/delete credentials for one provider."""

    def __init__(self, provider: str):
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider '{provider}'. Known: {', '.join(PROVIDERS)}")
        self.provider = provider
        self.env_var = PROVIDERS[provider][0]

    def get(self) -> Optional[str]:
        value = os.getenv(self.env_var)
        if value:
            return value
        if KEYRING_AVAILABLE:
            try:
                return keyring.get_password(KEYRING_SERVICE, self.provider)
            except Exception:
                return None
        return None

    def get_source(self) -> Optional[str]:
        """Where the credential came from: 'env', 'keyring', or None."""
        if os.getenv(self.env_var):
            return "env"
        if KEYRING_AVAILABLE:
            try:
                if keyring.get_password(KEYRING_SERVICE, self.provider):
                    return "keyring"
            except Exception:
                return None
        return None

    def set(self, value: str) -> None:
        if not KEYRING_AVAILABLE:
            raise RuntimeError(
                "No keyring backend available. Set the credential via the "
                f"{self.env_var} environment variable or a .env file instead."
            )
        keyring.set_password(KEYRING_SERVICE, self.provider, value)

    def delete(self) -> bool:
        """Remove from keyring. Returns True if something was deleted."""
        if not KEYRING_AVAILABLE:
            return False
        try:
            if keyring.get_password(KEYRING_SERVICE, self.provider):
                keyring.delete_password(KEYRING_SERVICE, self.provider)
                return True
        except Exception:
            pass
        return False


def get_credential(provider: str) -> Optional[str]:
    return CredentialStore(provider).get()


def export_to_env() -> None:
    """
    Backfill os.environ from the keyring for any provider not already set.

    Called once at CLI/TUI startup so every engine and summarizer - which
    read env vars - transparently honors keyring-stored credentials without
    each call site knowing about the store.
    """
    for provider, (env_var, _) in PROVIDERS.items():
        if not os.getenv(env_var):
            value = CredentialStore(provider).get()
            if value:
                os.environ[env_var] = value


def auth_overview() -> dict:
    """Status of every provider plus the Claude Code CLI backend."""
    import shutil
    rows = {}
    for provider, (env_var, unlocks) in PROVIDERS.items():
        store = CredentialStore(provider)
        source = store.get_source()
        rows[provider] = {
            "env_var": env_var,
            "configured": source is not None,
            "source": source,
            "unlocks": unlocks,
        }
    rows["claude-cli"] = {
        "env_var": None,
        "configured": shutil.which("claude") is not None,
        "source": "PATH" if shutil.which("claude") else None,
        "unlocks": "Claude subscription summaries - no API key needed",
    }
    return rows
