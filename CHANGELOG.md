# Changelog

All notable changes to Sonopsis are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow semver.

## [0.2.0] - 2026-06-12

The "engines and evidence" release: three new transcription engines, a
summarization backend that needs no API key, and a benchmark suite with
known-good corpora so every default is now backed by a measured result
rather than a leaderboard claim.

### Added

- **Claude Code CLI summarization** (`claude-cli`, `claude-cli/sonnet|opus|haiku`):
  headless Claude on the user's Pro/Max subscription - no API key, no
  per-token cost. Auto-preferred default when the CLI is installed.
- **NVIDIA Parakeet engine** (`parakeet`): TDT 0.6B v3 via onnx-asr - pure
  Python, no PyTorch, ~670MB int8 model. Auto-default when its extra is
  installed; benchmarked at 0% WER on clean wideband audio vs Whisper's 3-20%.
- **Local speaker diarization** (`parakeet-dia`): pyannote community-1 finds
  speaker turns, Parakeet transcribes each one. Beats ElevenLabs on
  crosstalk (9.0% vs 15.0% DER) on the project corpus.
- **OpenAI engine** (`openai`): gpt-4o-transcribe-diarize with speaker
  labels and timestamps. Best speaker counting measured - 9/9 perfect
  including a 5-speaker conversation, unhinted. Auto re-encodes oversized
  (>25MB) and format-rejected uploads to Opus.
- **Speaker-count controls**: `--num-speakers N` (measured: recovers missed
  speakers, DER -6 to -10 pts) and `--auto-speakers` (LLM inference from
  video metadata via Claude CLI, applied only at high confidence).
- **Benchmark suite** (`benchmarks/`, `scripts/benchmark_*.py`,
  `scripts/make_diarization_corpus.py`): WER and DER rubrics against
  exact-reference corpora - 21 transcription samples across clean/noisy/
  narrowband conditions, 10 multi-speaker conversations (2-5 speakers,
  noise, crosstalk, held-out set) with by-construction RTTMs.
- **Resumable playlists**: `--skip-existing` skips videos that already have
  a summary on disk.
- **Optional-extra installs**: `uv sync --extra whisper|elevenlabs|parakeet|diarize`
  keeps the core install light (~50MB); heavy engines are opt-in.
- **`sonopsis-tui` entry point** for the interactive interface.
- **Configuration actually loads**: `config.yaml` (defaults, paths) is read
  at startup via `utils/config.py`; previously it was documented but ignored.
- **Test suite**: 44 -> 127 unit tests plus gated end-to-end tests covering
  the real download -> transcribe -> summarize pipeline and live API contracts.

### Changed

- Default transcription engine is auto-selected: `parakeet` when installed,
  else `whisper`. Default summary model: `claude-cli` when the CLI is
  installed, else `claude-sonnet-4-6`.
- Long-audio chunking snaps to detected silences instead of hard time cuts
  (boundary stress test: 43.4% WER -> 0.0%).
- Model lineup refreshed to current IDs (`claude-sonnet-4-6`,
  `claude-haiku-4-5`, `claude-opus-4-8`, `gpt-5.1`) in a single registry
  (`utils/models.py`) consumed by menus, CLI and the summarizer.
- `main.py` and `sonopsis.py` share one pipeline (`utils/pipeline.py`)
  instead of drifting duplicates.
- Interactive menus work cross-platform (numbered-input fallback off
  Windows) and only offer engines/models whose dependencies and keys exist.
- Utility scripts (`compare_models.py`, `process_existing.py`) take CLI
  arguments instead of hardcoded file paths.
- Documented Python requirement corrected to 3.11+; `requirements.txt` is
  now a legacy pointer to the pyproject extras.

### Fixed

- Watch URLs carrying `&list=` no longer trigger whole-playlist processing.
- Unattended runs no longer hang on the cached-audio prompt (`isatty` + EOF
  detection); reused audio files are never deleted by cleanup.
- `--help` works without API keys (argument parsing happens before the
  backend check), restoring the previously skipped CLI test class.
- Windows consoles no longer crash on emoji/Unicode output.
- Transient API errors (429/5xx/network) retry with exponential backoff
  instead of discarding a finished transcription.
- Failed video-ID extraction no longer produces invalid `YT_N/A_*` filenames.
- WhisperX no longer eagerly loads a duplicate Whisper model as a fallback.
- Whisper's style prompt no longer biases transcription toward
  technology-podcast vocabulary on unrelated content.

### Removed

- Unused `rich` dependency.
- ~200 lines of dead interactive-menu code (including a latent `KeyError`).
- Dead SRT timestamp parser.

## [0.1.0] - 2026-04

- Initial release: YouTube download (yt-dlp), Whisper/WhisperX/ElevenLabs
  transcription, GPT/Claude/OpenRouter summarization, interactive menu and
  CLI front-ends, prompt templates in `prose/`.
