# AGENTS.md - AI Assistant Instructions

## Project Overview

**Sonopsis** is a video/audio summarizer that downloads YouTube videos, transcribes them using multiple engines, and generates AI-powered summaries.

**Stage:** Promoted (stable, own repo, documented)

**Core Workflow:**
1. Download YouTube video/audio via yt-dlp
2. Transcribe using Whisper, WhisperX, or ElevenLabs
3. Summarize using GPT/Claude/OpenRouter models
4. Output markdown summaries with metadata

## Key Files

| File | Purpose |
|------|---------|
| `sonopsis.py` | Interactive menu interface (recommended entry point) |
| `main.py` | CLI interface for scripting/automation |
| `utils/downloader.py` | YouTube download via yt-dlp |
| `utils/transcriber.py` | Multi-engine transcription (Whisper, WhisperX, ElevenLabs) |
| `utils/summarizer.py` | LLM summarization (OpenAI, Anthropic, OpenRouter) |

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
- Python 3.8+ compatible
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
1. Add model name to `utils/summarizer.py` `__init__` docstring
2. Handle API-specific parameters in `summarize()` method
3. Update model selection in `sonopsis.py` menu

### New Transcription Engine
1. Add engine to `utils/transcriber.py`
2. Update CLI args in `main.py`
3. Add menu option in `sonopsis.py`

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

Currently manual testing. When adding features:
1. Test with short video first (< 5 min)
2. Test all transcription engines if touching that code
3. Test both CLI and interactive modes

## Dependencies

External services required:
- YouTube (video source)
- OpenAI API (optional, for GPT models)
- Anthropic API (optional, for Claude models)
- OpenRouter API (optional, for Kimi/GLM models)
- ElevenLabs API (optional, for cloud transcription)
- Hugging Face (optional, for WhisperX speaker diarization)

Local requirements:
- FFmpeg (required for audio processing)
- Python packages per `requirements.txt`
