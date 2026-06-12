# AGENTS.md - AI Assistant Instructions

## Project Overview

**Sonopsis** is a video/audio summarizer that downloads YouTube videos, transcribes them using multiple engines, and generates AI-powered summaries.

**Stage:** Promoted (stable, own repo, documented)

**Core Workflow:**
1. Download YouTube video/audio via yt-dlp
2. Transcribe using one of six engines: Parakeet (default local), Parakeet-dia,
   Whisper, WhisperX, ElevenLabs, OpenAI gpt-4o-transcribe-diarize
3. Summarize using the Claude Code CLI (default when installed) or
   GPT/Claude/OpenRouter API models
4. Output markdown summaries with metadata

## Key Files

| File | Purpose |
|------|---------|
| `sonopsis.py` | Interactive menu interface (recommended entry point) |
| `main.py` | CLI interface for scripting/automation |
| `utils/pipeline.py` | Shared download->transcribe->summarize flow (both front-ends call this) |
| `utils/downloader.py` | YouTube download via yt-dlp |
| `utils/transcriber.py` | Multi-engine transcription behind `AudioTranscriber(engine=...)` |
| `utils/summarizer.py` | LLM summarization (OpenAI, Anthropic, OpenRouter, Claude Code CLI) |
| `utils/models.py` | Summarization model registry (IDs, costs, limits) - single source of truth |
| `utils/speakers.py` | Gated LLM speaker-count inference (`--auto-speakers`) |
| `utils/config.py` | `config.yaml` loader + engine auto-default |
| `benchmarks/` | Known-good corpora + committed WER/DER results; defaults must stay evidence-backed |
| `scripts/benchmark_*.py` | WER and DER benchmark harnesses |

## LLM Artifacts (prose/)

All prompts and templates live in `prose/`:

| Path | Purpose |
|------|---------|
| `prose/prompts/system.md` | System prompt for summarization |
| `prose/prompts/analysis_basic.md` | Basic 5-section analysis prompt |
| `prose/prompts/analysis_advanced.md` | Advanced 9-section narrative prompt |
| `prose/protocols/speaker_identification.md` | Speaker diarization guidance |

## Configuration

- **Secrets:** `.env` file (API keys) - never commit
- **Config:** `config.yaml` for non-secret settings
- **Defaults:** Code has sensible defaults; config is optional

## Patterns & Conventions

### File Naming
- Transcripts: `YT_{video_id}_{title}_transcript.md`
- Summaries: `YT_{video_id}_{title}_summary.md`
- Use kebab-case for new files

### Code Style
- Python 3.11+ compatible
- Type hints for function signatures
- Docstrings for public functions
- External prompts in `prose/` (not hardcoded strings)

### Output Directories
- `downloads/` - Temporary audio files (auto-cleaned)
- `transcripts/` - Generated transcripts
- `summaries/` - AI-generated summaries

These directories contain user output, not code. Don't commit contents.

## Adding New Features

### New LLM Model Support
1. Add the model to the registry in `utils/models.py` (label, provider, cost, max_tokens)
2. Handle any API-specific parameters in `utils/summarizer.py` `_generate_once()`
3. Menus and CLI pick it up automatically from the registry

### New Transcription Engine
1. Add an init branch + `_transcribe_<engine>()` method in `utils/transcriber.py`
   and route it in `transcribe()`
2. Add the engine to `ENGINE_DISPLAY` in `utils/pipeline.py`
3. Add it to the `--transcription-engine` choices in `main.py` and the menu in `sonopsis.py`
4. Heavy dependencies go in a new optional extra in `pyproject.toml`, with a
   friendly ImportError hint (see `_import_onnx_asr` for the pattern)
5. Benchmark it: `python scripts/benchmark_engines.py --engines <engine>` (and
   `benchmark_diarization.py` if it diarizes) - update the README engine table
   with measured numbers, not vendor claims

### New Analysis Mode
1. Create `prose/prompts/analysis_{mode}.md`
2. Add mode to CLI args
3. Update menu selection

## What NOT to Do

- Don't hardcode prompts in Python - use `prose/` files
- Don't commit `.env` or API keys
- Don't commit contents of `downloads/`, `transcripts/`, `summaries/`
- Don't add complex abstractions - keep it simple
- Don't add features without clear use case (YAGNI)
- Don't break CLI compatibility without good reason

## Testing

```bash
uv run --extra dev pytest tests -q              # unit suite (~127 tests, fast, no network)
RUN_E2E=1 uv run --extra dev --extra whisper pytest tests/e2e -v   # real pipeline + live APIs
python scripts/benchmark_engines.py             # WER vs known-good corpus
python scripts/benchmark_diarization.py         # DER vs exact RTTMs
```

When adding features:
1. Unit tests are mandatory; mock network/model access (see existing test files)
2. Touching engine code? Run the relevant benchmark and the gated e2e tests
3. Test with a short video first (the e2e suite uses the 19s "Me at the zoo")
4. Test both CLI and interactive modes

## Dependencies

External services required:
- YouTube (video source)
- OpenAI API (optional, for GPT models)
- Anthropic API (optional, for Claude models)
- Claude Code CLI (optional, `claude-cli*` models - summarizes on the user's Claude subscription, no API key)
- OpenRouter API (optional, for Kimi/GLM models)
- ElevenLabs API (optional, for cloud transcription)
- Hugging Face token (optional, for pyannote diarization - parakeet-dia and
  WhisperX; requires accepting terms on the gated pyannote models, including
  `pyannote/speaker-diarization-community-1` for pyannote 4.x)

Local requirements:
- FFmpeg (required for audio processing)
- Python 3.11+; dependencies via `uv sync` plus optional extras
  (`whisper`, `parakeet`, `diarize`, `elevenlabs`) - `requirements.txt`
  is a legacy pip fallback only
