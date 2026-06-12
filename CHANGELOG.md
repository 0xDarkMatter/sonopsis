# Changelog

All notable changes to Sonopsis are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow semver.

## [0.3.0] - 2026-06-12

The agent-first CLI rewrite: a typer command architecture with JSON output,
semantic exit codes and keyring auth, replacing the argparse single-command
app. Engine and benchmark internals carry over unchanged; every pre-0.3.0
invocation keeps working through compatibility shims.

### Added

- **Typer CLI** (`src/sonopsis/cli.py`): `summarise` (playlists included),
  `transcribe` (URLs *and local audio files* - new capability), `engines
  list|install`, `models list`, `auth login|status|logout`, `config show`,
  `tui`.
- **`--json` everywhere**: `{data, meta}` envelopes on stdout; errors as
  `{"error": {code, message}}`. stdout carries only data - all progress and
  chrome go to stderr, so piped output stays clean.
- **Semantic exit codes**: 0 success, 1 error, 2 auth required, 3 not found,
  4 validation.
- **Keyring credential store** (`sonopsis auth login <provider>`): resolution
  order env > .env > keyring, providers openai/anthropic/openrouter/
  elevenlabs/hf; backfilled into the environment at startup so engines need
  no changes.
- **`sonopsis engines install <pack>`**: self-managing engine packs - no more
  raw `uv sync --extra` on the user surface.
- **Agent skill** (`skills/sonopsis/`): SKILL.md + benchmark-backed engine
  selection reference for AI-assistant orchestration.

### Changed

- `src/sonopsis/` package layout with a hatchling build; prompt templates
  (`prose/`) now ship inside the package, fixing the editable-install-only
  packaging limitation.
- The interactive interface is `sonopsis tui`; its ASCII-art banner is
  replaced by a quiet one-line header.
- Compatibility shims: `sonopsis <URL>` implies `summarise`; engine shortcut
  flags and the old `--transcription-engine`/`--gpt-model` spellings are
  rewritten on the way in.

### Removed

- Top-level `main.py`/`sonopsis.py` entry scripts and the `utils/` package
  (now `src/sonopsis/`). Library imports change from `utils.X` to
  `sonopsis.X` - the only breaking change for programmatic users.

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
- **Shorter CLI flags**: `--engine` and `--model` are the primary spellings;
  `--transcription-engine` and `--gpt-model` remain as compatible aliases.
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

## [0.1.0] - 2026-04-04

First tagged release, packaging six months of development for installation
via `uv tool install`. The phases below were untagged; dates are from
commit history.

### Packaging (2026-04)

- `pyproject.toml` with Forma metadata; `sonopsis` console entry point.
- Initial pytest suite (imports, config shape, prose files, CLI parser,
  summarizer utilities).

### Structure reorganisation (2026-01)

- LLM artifacts moved into `prose/` (system prompt, basic/advanced analysis
  prompts, speaker-identification protocol) - prompts are files, not
  hardcoded strings.
- `AGENTS.md` (AI assistant instructions) and `config.yaml` introduced.
- Output conventions settled: `downloads/`, `transcripts/`, `summaries/`.

### Multi-engine, multi-model era (2025-11)

- **ElevenLabs Scribe** cloud transcription: SRT timestamps, speaker
  diarization, audio-event tags, clickable YouTube bookmark links in
  summaries.
- Multi-provider summarization: Anthropic Claude and OpenRouter
  (Kimi K2, GLM) alongside OpenAI GPT.
- `YT_{video_id}_{title}` file naming plus comprehensive YouTube metadata
  in summary headers (views, likes, tags, chapters, description).
- Speaker-identification system: SPEAKER_X labels mapped to real names
  using title/description clues.

### Initial release (2025-10)

- Core pipeline: yt-dlp download -> Whisper transcription -> GPT
  summarization, with playlist batch processing.
- **WhisperX** engine with optional pyannote speaker diarization
  (HF token onboarding flow, GPU detection).
- Interactive menu interface (arrow-key navigation) and scriptable CLI.
- Basic (5-section) and Advanced (9-section) analysis modes with external
  prompt templates.
