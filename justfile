# Sonopsis task runner - run `just` to list commands.
# Recipes use sh (ships with Git on Windows). Raw uv equivalents are shown
# in README "Advanced Setup & Configuration" if you don't use just.

# List available commands
default:
    @just --list

# One-time setup: core deps + recommended local engine (Parakeet) + dev tools
setup:
    uv sync --extra parakeet --extra dev

# Add an engine pack without removing the ones you already have.
# Packs: parakeet | whisper | diarize | elevenlabs
engine pack:
    uv sync --inexact --extra {{pack}}

# Install every engine pack (largest download; whisper pulls ~2GB PyTorch)
engines-all:
    uv sync --extra parakeet --extra whisper --extra diarize --extra elevenlabs --extra dev

# Summarise a video or playlist (flags pass through, e.g. just summarise URL --engine openai)
summarise +args:
    uv run python main.py {{args}}

# Alias for summarise
run +args:
    uv run python main.py {{args}}

# Launch the interactive menu interface
tui:
    uv run python sonopsis.py

# Run the unit test suite (fast, no network)
test:
    uv run --extra dev pytest tests -q --ignore=tests/e2e

# Run end-to-end tests against real backends (network + API keys required)
e2e:
    RUN_E2E=1 uv run --extra dev --extra whisper --extra parakeet pytest tests/e2e -v

# Benchmark transcription engines against the known-good corpus (WER)
bench *engines="parakeet whisper:base":
    uv run --extra parakeet --extra whisper --extra elevenlabs --extra dev python scripts/benchmark_engines.py --engines {{engines}}

# Benchmark speaker diarization (DER vs exact reference RTTMs)
bench-dia *engines="parakeet-dia":
    uv run --extra parakeet --extra whisper --extra diarize --extra elevenlabs --extra dev python scripts/benchmark_diarization.py --engines {{engines}}

# Regenerate the diarization conversation corpora
corpus:
    uv run --extra dev python scripts/make_diarization_corpus.py
