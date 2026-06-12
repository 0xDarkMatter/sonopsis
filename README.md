```
███████╗ ██████╗ ███╗   ██╗ ██████╗ ██████╗ ███████╗██╗███████╗
██╔════╝██╔═══██╗████╗  ██║██╔═══██╗██╔══██╗██╔════╝██║██╔════╝
███████╗██║   ██║██╔██╗ ██║██║   ██║██████╔╝███████╗██║███████╗
╚════██║██║   ██║██║╚██╗██║██║   ██║██╔═══╝ ╚════██║██║╚════██║
███████║╚██████╔╝██║ ╚████║╚██████╔╝██║     ███████║██║███████║
╚══════╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝╚══════╝
```

# Sonopsis

**Video/Audio Summariser** - Download · Transcribe · Summarize

A Python application that downloads YouTube videos, transcribes them across six engines (local and cloud), and generates comprehensive summaries and notes using Claude/GPT models - or your Claude subscription, no API key needed.

## Quick Start

Three steps to your first summary. You need [Python 3.11+](https://www.python.org/downloads/), [uv](https://docs.astral.sh/uv/) and [FFmpeg](https://ffmpeg.org/download.html) (`choco install ffmpeg` / `brew install ffmpeg` / `apt install ffmpeg`).

```bash
# 1. Get the code and dependencies (incl. the recommended local transcription engine)
git clone https://github.com/0xDarkMatter/sonopsis && cd sonopsis
uv sync --extra parakeet

# 2. Pick ONE summarization backend:
#    - Already use Claude Code (Pro/Max)? Skip this step - it's detected automatically.
#    - Otherwise: cp .env.example .env  and add OPENAI_API_KEY or ANTHROPIC_API_KEY

# 3. Summarize a video
uv run python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Your transcript lands in `transcripts/`, the summary in `summaries/`. Prefer guided menus over flags? Run `uv run python sonopsis.py` instead. Everything else - speaker diarization, engine choices, playlists, custom prompts - is below.

## Recent Updates

**v0.2.0** (June 2026)

*   🚀 **Claude Code CLI summarization** - Summarize on your Claude Pro/Max subscription with no API key: `--model claude-cli` (or `/sonnet`, `/opus`, `/haiku`). Auto-selected as the default whenever the CLI is installed.
*   🆕 **NVIDIA Parakeet engine, new local default** - TDT 0.6B v3 via onnx-asr: no PyTorch, ~670MB, and 0% WER on clean wideband audio where Whisper scored 3-20% on the project's known-good corpus. `uv sync --extra parakeet`.
*   🗣️ **Free local speaker diarization** - `parakeet-dia` pairs pyannote speaker turns with Parakeet transcription, beating ElevenLabs on crosstalk (9.0% vs 15.0% DER). `--num-speakers N` sharpens it further; `--auto-speakers` infers the count from video metadata, applied only at high confidence.
*   🔌 **OpenAI gpt-4o-transcribe-diarize engine** - The best speaker counter measured: 9/9 perfect counts unhinted, including a 5-speaker panel. Reuses your existing `OPENAI_API_KEY`; oversized or rejected uploads auto re-encode to Opus.
*   🧪 **Benchmark suite with known-good corpora** - WER and DER rubrics against exact-reference audio (31 samples across clean, noisy, narrowband, crosstalk and multi-speaker conditions). Every engine default above is backed by a committed result in `benchmarks/`, not a leaderboard claim.
*   ⚡ **Silence-aligned chunking** - Long-audio chunk boundaries snap to detected silences instead of cutting mid-word; a forced-boundary stress test went from 43.4% WER to 0.0%.
*   🔧 **Quality-of-life overhaul** - `config.yaml` is actually loaded now, playlists resume with `--skip-existing`, menus work beyond Windows, transient API errors retry, flags got shorter (`--engine`, `--model`; old spellings still work), and the suite grew from 44 to 127 tests plus gated e2e runs against real backends.

[View full changelog →](CHANGELOG.md)

## Which Engine & Model Should I Use?

Picks below are backed by the measured results in [`benchmarks/`](benchmarks/).

**Transcription** (`--engine`):

| Your situation | Use | Why |
|---|---|---|
| Default / best free accuracy | `parakeet` | 0% WER on clean wideband in the project corpus; no PyTorch, CPU-friendly |
| Interview or podcast, want speaker labels, free | `parakeet-dia` | Free local diarization; add `--num-speakers 2` or `--auto-speakers` |
| Panel with 3-5+ speakers | `openai` | Best speaker counting measured: 9/9 perfect, unhinted |
| Heavy crosstalk / people talking over each other | `parakeet-dia` | Best overlap handling measured (9.0% DER) |
| Clickable YouTube timestamp bookmarks in summaries | `elevenlabs` | Word-level timestamps + audio events; 2.5h/month free tier |
| Phone-quality, archival or noisy-telephony audio | `whisper` | Most robust engine on genuinely degraded recordings |
| Non-European languages | `elevenlabs` | 99 languages (Parakeet covers 25 European) |
| No local installs at all | `elevenlabs` or `openai` | Cloud-only; core install stays ~50MB |

**Summarization** (`--model`):

| Your situation | Use | Why |
|---|---|---|
| Claude Pro/Max subscriber | `claude-cli` | No API key, no per-token cost (default when installed) |
| Highest quality summary | `claude-cli/opus` or `claude-opus-4-8` | Most capable Claude |
| Best API quality/cost balance | `claude-sonnet-4-6` | Default API model |
| Cheapest | `claude-haiku-4-5-20251001` or `gpt-4o-mini` | ~$0.05-0.08 per 3-hour video |
| Very long (multi-hour) transcripts | `openrouter/moonshot/kimi-k2` | 200K+ context specialist |
| Chinese / multilingual content | `openrouter/zhipuai/glm-4.6-plus` | Strongest multilingual option |

## Features

- **Interactive Menu Interface**: Beautiful Claude Code-style menus with keyboard navigation
- **Download YouTube Videos**: Automatically downloads videos and extracts audio
- **Playlist Batch Processing**: Process entire YouTube playlists with one command
- **Six Transcription Engines**:
  - **Parakeet** (default when installed): NVIDIA TDT 0.6B v3 - local, free, no PyTorch, beats Whisper accuracy on the project benchmarks
  - **Parakeet-dia**: Parakeet + pyannote speaker diarization (free, local, requires HF token)
  - **Whisper**: Local transcription (free, robust on degraded audio)
  - **WhisperX**: Local with speaker diarization (free, requires HF token)
  - **ElevenLabs**: Cloud transcription (paid, 99 languages, speaker diarization + audio events)
  - **OpenAI**: gpt-4o-transcribe-diarize (paid, best speaker counting measured, reuses your OpenAI key)
- **Speaker Intelligence**: `--num-speakers` hints and `--auto-speakers` (LLM infers the count from video metadata, applied only at high confidence)
- **Benchmarked Defaults**: engine choices are backed by committed WER/DER results against known-good corpora in `benchmarks/`
- **YouTube Bookmark Links**: ElevenLabs transcripts include clickable timestamps that jump to exact moments in the video
- **Two Analysis Modes**: Choose between Basic (5 sections) or Advanced (9 sections) summaries
- **External Prompt Files**: Easily customize analysis prompts via markdown files
- **AI-Powered Summaries**: Generates well-formatted summaries with timestamps, quotes, and references
- **Multiple AI Models**:
  - Claude Code CLI: uses your Claude Pro/Max subscription - no API key or per-token cost (`claude-cli`, `claude-cli/sonnet`, `claude-cli/opus`, `claude-cli/haiku`)
  - Anthropic: Claude Sonnet 4.6, Claude Haiku 4.5, Claude Opus 4.8
  - OpenAI: GPT-4o-mini, GPT-4o, GPT-5.1
  - OpenRouter: Kimi K2, GLM 4.6
- **Customizable Whisper Models**: Choose from tiny, base, small, medium, or large models
- **Progress Tracking**: Real-time progress updates for batch processing

## Prerequisites

- Python 3.11 or higher
- FFmpeg (required for audio processing)
- A summarization backend: OpenAI/Anthropic/OpenRouter API key, or the Claude Code CLI (uses your Claude subscription)

### Installing FFmpeg

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg  # CentOS/RHEL
```

## Advanced Setup & Configuration

Everything past the Quick Start: engine packs, API keys, and per-project defaults.

1. **Clone or download this repository**

2. **Install Python dependencies:**
```bash
# Core install (summarization + ElevenLabs/OpenAI cloud engines, no local models)
uv sync

# Engine packs - install only what you need:
uv sync --extra parakeet    # NVIDIA Parakeet, recommended local engine (~70MB deps, no PyTorch)
uv sync --extra whisper     # Whisper/WhisperX (downloads PyTorch CPU wheels, ~2GB)
uv sync --extra diarize     # pyannote speaker diarization for parakeet-dia/WhisperX
uv sync --extra elevenlabs  # ElevenLabs cloud SDK

# Extras combine freely:
uv sync --extra parakeet --extra diarize

# Legacy pip fallback
pip install -r requirements.txt
```

> **Why "--extra"?** These are standard Python [optional dependencies](https://packaging.python.org/en/latest/specifications/dependency-groups/)
> (the packaging ecosystem calls them "extras" - the same mechanism as
> `pip install "sonopsis[parakeet]"`). uv spells it `--extra <name>`. Sonopsis
> uses them so the core install stays ~50MB: heavy engine stacks like PyTorch
> are opt-in rather than forced on everyone.

> **No API key?** If the [Claude Code CLI](https://claude.com/claude-code) is installed,
> Sonopsis automatically uses it for summarization on your Claude Pro/Max subscription -
> no `ANTHROPIC_API_KEY` needed. Select "Claude Code (Max plan)" in the interactive menu,
> or pass `--model claude-cli` (optionally `claude-cli/sonnet`, `claude-cli/opus`,
> `claude-cli/haiku`).

3. **Set up your API keys:**
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key (required for summarization)
   - Optionally add ElevenLabs API key for cloud transcription
```bash
cp .env.example .env
# Edit .env and add your API keys
```

Your `.env` file should look like:
```
OPENAI_API_KEY=sk-your-api-key-here
SUMMARY_MODEL=gpt-4o-mini
WHISPER_MODEL=base

# Optional: For ElevenLabs cloud transcription
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional: For WhisperX speaker diarization
HF_TOKEN=your_huggingface_token_here
```

**Getting API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- ElevenLabs: https://elevenlabs.io (sign up and get API key from dashboard)
- Hugging Face: https://huggingface.co/settings/tokens (for WhisperX speaker diarization)

## Project Structure

```
Sonopsis/
├── sonopsis.py              # Interactive menu interface (recommended)
├── main.py                  # Command-line interface
├── pyproject.toml           # Project metadata + dependencies (uv-managed)
├── config.yaml              # Non-secret defaults (models, paths)
├── .env.example             # API key template
├── LICENSE                  # MIT license
├── utils/                   # Core modules
│   ├── downloader.py        # YouTube video/audio download
│   ├── transcriber.py       # Whisper/WhisperX/ElevenLabs transcription
│   ├── summarizer.py        # GPT/Claude/OpenRouter/Claude-CLI summarization
│   ├── pipeline.py          # Shared download->transcribe->summarize flow
│   ├── models.py            # AI model registry (IDs, costs, limits)
│   └── config.py            # config.yaml loader
├── prose/                   # LLM prompts and protocols
│   ├── prompts/system.md            # AI system prompt
│   ├── prompts/analysis_basic.md    # Basic analysis prompt
│   ├── prompts/analysis_advanced.md # Advanced analysis prompt
│   └── protocols/speaker_identification.md
├── scripts/                 # Utility scripts
│   ├── compare_models.py    # Compare AI model outputs on one transcript
│   └── process_existing.py  # Transcribe + summarize a local audio file
├── tests/                   # Unit tests (pytest) + e2e suite
├── docs/                    # Documentation
│   └── PLAN.md              # Future enhancements
├── downloads/               # Temporary audio files (auto-cleaned)
├── transcripts/             # Generated transcripts
└── summaries/               # AI-generated summaries
```

## Usage

### Interactive Mode (Recommended)

```bash
python sonopsis.py
```

**Features:**
- Step-by-step guided interface with beautiful colored menus
- Interactive model selection with descriptions
- Shows already-downloaded Whisper models
- Clear cost and speed information with visual tags
- Analysis mode selection (Basic or Advanced)
- Process multiple videos in one session

### Command Line Mode

```bash
python main.py <YouTube_URL>
```

### Examples

```bash
# Process a single video with default settings (local Whisper)
python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Summarize on your Claude subscription via the Claude Code CLI (no API key)
python main.py <URL> --model claude-cli
python main.py <URL> --model claude-cli/opus

# Process an entire playlist
python main.py "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

# Local diarization: Parakeet + pyannote, auto-inferring the speaker count
python main.py <URL> --engine parakeet-dia --auto-speakers

# Local diarization with a known speaker count (measurably more accurate)
python main.py <URL> --engine parakeet-dia --num-speakers 2

# Use WhisperX for speaker diarization (local, free)
python main.py <URL> --engine whisperx

# Use ElevenLabs for cloud transcription (99 languages, speaker diarization)
python main.py <URL> --engine elevenlabs

# Use OpenAI gpt-4o-transcribe-diarize (best speaker counting measured)
python main.py <URL> --engine openai

# Use a larger Whisper model for better accuracy
python main.py https://youtu.be/dQw4w9WgXcQ --whisper-model small

# Use Claude Sonnet for highest quality summaries
python main.py <URL> --model claude-sonnet-4-6

# Use GPT-5.1 for complex reasoning
python main.py <URL> --model gpt-5.1

# Use Kimi K2 (long context specialist via OpenRouter)
python main.py <URL> --model openrouter/moonshot/kimi-k2

# Use GLM 4.6 Plus (Chinese + multilingual via OpenRouter)
python main.py <URL> --model openrouter/zhipuai/glm-4.6-plus

# Process playlist with ElevenLabs transcription and Claude
python main.py <PLAYLIST_URL> --engine elevenlabs --model claude-haiku-4-5-20251001

# Keep downloaded audio files
python main.py <URL> --keep-files
```

### Command Line Options

- `url` (required): YouTube video or playlist URL
- `--engine` (alias `--transcription-engine`): Transcription engine to use (default: `whisper`)
  - `whisper`: Local transcription, free, no speaker labels
  - `whisperx`: Local with speaker diarization, free (requires HF_TOKEN)
  - `elevenlabs`: Cloud transcription, paid, 99 languages, speaker diarization + audio events
- `--whisper-model`: Whisper model size - `tiny`, `base`, `small`, `medium`, `large` (default: `base`)
  - Only applies to `whisper` and `whisperx` engines
- `--model` (alias `--gpt-model`): AI model for summaries (default: `claude-cli` when the Claude Code CLI is installed, else `claude-sonnet-4-6`)
  - Claude Code CLI (subscription): `claude-cli`, `claude-cli/sonnet`, `claude-cli/opus`, `claude-cli/haiku`
  - Anthropic Claude: `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-opus-4-8`
  - OpenAI: `gpt-4o-mini`, `gpt-4o`, `gpt-5.1`
  - OpenRouter: `openrouter/moonshot/kimi-k2`, `openrouter/zhipuai/glm-4.6-plus`
- `--analysis-mode`: Analysis mode - `basic` or `advanced` (default: `basic`)
- `--keep-files`: Keep downloaded audio files after processing
- `--start-from`: Start processing from video number (for playlists, default: 1)
- `--skip-existing`: Skip videos that already have a summary on disk (makes playlist runs resumable)
- `--num-speakers N`: Known speaker count for diarizing engines (`parakeet-dia`) - measurably improves speaker detection
- `--auto-speakers`: Infer the speaker count from video metadata via the Claude Code CLI (applied only at high confidence; a few seconds per video)

Defaults for models, engine, analysis mode and output paths can also be set in `config.yaml`.

### Playlist Processing

The tool automatically detects playlist URLs and processes all videos sequentially:

- Extracts all video URLs from the playlist
- Shows a summary before starting (total videos, models, etc.)
- Processes each video one at a time with progress tracking
- Provides a final summary showing successful/failed videos
- All transcripts and summaries are saved individually in their respective folders

### Transcription Engine Comparison

| Engine      | Cost  | Speed      | Languages | Speaker ID | Audio Events | Timestamps | Notes                           |
|-------------|-------|------------|-----------|------------|--------------|------------|--------------------------------|
| Parakeet    | Free  | Very Fast  | 25 (EU)   | No         | No           | No         | NVIDIA TDT 0.6B v3 - beats Whisper accuracy, no PyTorch, ~670MB model, CPU-friendly (`--extra parakeet`) |
| Parakeet-dia| Free  | Medium     | 25 (EU)   | Yes        | No           | Turn-level | Parakeet + pyannote; best crosstalk handling measured (`--extra parakeet --extra diarize` + HF token) |
| Whisper     | Free  | Fast       | ~60       | No         | No           | No         | Most robust on degraded/telephony audio (`--extra whisper`) |
| WhisperX    | Free  | Medium     | ~60       | Yes        | No           | No         | Requires HF token, GPU recommended (`--extra whisper --extra diarize`) |
| ElevenLabs  | Paid* | Very Fast  | 99        | Yes (32)   | Yes          | Word-level | Cloud-based, YouTube bookmarks  |
| OpenAI      | Paid ($0.36/hr) | Very Fast | ~60 | Yes      | No           | Yes        | gpt-4o-transcribe-diarize - best speaker counting measured (9/9 unhinted); >25MB uploads auto re-encoded |

\* ElevenLabs offers a free tier with 2.5 hours/month included

**When to use each engine:**
- **Whisper**: Quick transcription, no speaker identification needed, offline use
- **WhisperX**: Free speaker diarization, good GPU available, offline use
- **ElevenLabs**: Need 99 language support, don't have GPU, want audio events + clickable YouTube timestamp bookmarks

**ElevenLabs Timestamp Bookmarks:**

When using ElevenLabs transcription, the system preserves precise timestamps from the SRT output and formats them with speaker labels:

```markdown
**[SPEAKER_00]** `[00:01:23]` The text spoken at this moment, including [laughter] and other audio events...
```

The AI summaries can then convert these timestamps into clickable YouTube links:
- Format: `[00:12:34](https://youtu.be/VIDEO_ID?t=754s)`
- Clicking the timestamp jumps directly to that moment in the video
- Enables quick navigation and verification of claims
- Perfect for creating navigable, citation-rich summaries

This follows the same format YouTube uses for captions (SRT), ensuring maximum compatibility and token efficiency.

### Whisper Model Comparison (for Whisper & WhisperX)

| Model  | Size    | Speed    | Accuracy | Use Case                    |
|--------|---------|----------|----------|-----------------------------|
| tiny   | ~75 MB  | Fastest  | Good     | Quick tests, simple content |
| base   | ~150 MB | Fast     | Better   | General use (recommended)   |
| small  | ~500 MB | Medium   | Great    | Higher accuracy needed      |
| medium | ~1.5 GB | Slow     | Excellent| Professional transcription  |
| large  | ~3 GB   | Slowest  | Best     | Maximum accuracy            |

## Output Structure

The application creates three directories:

```
Sonopsis/
├── downloads/          # Downloaded audio files (deleted unless --keep-files)
├── transcripts/        # Timestamped markdown transcripts
│   └── *_transcript.md
└── summaries/          # AI-generated summaries
    └── *_summary.md
```

### Sample Output

**Transcript** (`transcripts/Video_Title_transcript.md`):
```markdown
# Transcript

**Language:** en
**Duration:** 00:15:42

---

**[00:00:15 -> 00:00:42]** Welcome to the show, today we're discussing...

**[00:00:43 -> 00:01:12]** That's a great question. I think the key is...
```

**Summary** (`summaries/Video_Title_summary.md`):
```markdown
# Video Summary: Video Title

**Channel:** Channel Name
**Duration:** 15m 30s
**URL:** https://youtube.com/watch?v=...
**Generated:** 2025-10-18 10:30:00

## Executive Summary
Brief overview of the video content...

## Key Topics & Main Points
- Topic 1
- Topic 2

## Detailed Notes
### Section 1
Detailed content...

## Key Takeaways
1. Important insight 1
2. Important insight 2

## Actionable Items
- Action item 1
```

## Module Documentation

| Module | Purpose |
|---|---|
| `utils/pipeline.py` | Shared download → transcribe → summarize flow used by both front-ends (`process_video()`) |
| `utils/downloader.py` | YouTube download via yt-dlp (`download_video()`, `get_playlist_videos()`, cached-audio reuse) |
| `utils/transcriber.py` | All six transcription engines behind one `AudioTranscriber(engine=...).transcribe()` interface |
| `utils/summarizer.py` | Summarization across OpenAI / Anthropic / OpenRouter APIs and the Claude Code CLI, with retry |
| `utils/models.py` | Single registry of summarization models (IDs, costs, output limits) feeding menus and CLI |
| `utils/speakers.py` | Gated LLM speaker-count inference from video metadata (`--auto-speakers`) |
| `utils/config.py` | `config.yaml` loader and engine auto-default logic |

## Benchmarks

Engine defaults are evidence-based: `benchmarks/` contains exact-reference
corpora (clean/noisy/narrowband speech with verified transcripts;
multi-speaker conversations with by-construction RTTMs) plus committed
results. Reproduce or extend with:

```bash
python scripts/benchmark_engines.py --engines parakeet whisper:base elevenlabs openai
python scripts/benchmark_diarization.py --engines parakeet-dia elevenlabs openai
python scripts/make_diarization_corpus.py   # regenerate conversation corpora
```

Headlines from the committed runs: Parakeet 0% WER on clean wideband (Whisper
3-20%); silence-aligned chunking eliminated boundary errors (43.4% → 0% on a
stress test); OpenAI counted speakers perfectly on 9/9 conversations; and
parakeet-dia beat ElevenLabs on crosstalk (9.0% vs 15.0% DER).

## Cost Considerations

**Transcription Costs:**
- **Whisper (local)**: Free after initial model download
- **WhisperX (local)**: Free (requires HF token for speaker diarization)
- **ElevenLabs (cloud)**:
  - Free tier: 2.5 hours/month included
  - Paid: $0.22-0.48 per additional hour depending on plan
  - For a 1-hour video: ~$0.22-0.48
  - For a 3-hour podcast: ~$0.66-1.44

**AI Model Pricing (per 3-hour video):**
- `gpt-4o-mini`: ~$0.05-0.10 (cheapest OpenAI)
- `gpt-4o`: ~$0.15-0.30
- `gpt-5.1`: ~$0.20-0.40 (latest reasoning model)
- `claude-haiku-4-5`: ~$0.03-0.10 (fastest, cheapest)
- `claude-sonnet-4-6`: ~`claude-sonnet-4-5`: ~$0.10-0.30 (best overall quality).10-0.30 (best overall quality)
- `claude-cli`: `claude-sonnet-4-5`: ~$0.10-0.30 (best overall quality) extra (uses your Claude subscription)
- `kimi-k2` (OpenRouter): ~$0.15-0.40 (200K+ context)
- `glm-4.6-plus` (OpenRouter): ~$0.10-0.25 (excellent multilingual)

**Total Cost Examples (3-hour video):**
- Whisper + GPT-4o-mini: ~$0.05-0.10 (cheapest)
- WhisperX + Claude Haiku: ~$0.03-0.10 (cheapest with speaker ID)
- ElevenLabs + Claude Sonnet: ~$0.76-1.74 (premium, 99 languages)
- ElevenLabs + Kimi K2: ~$0.81-1.84 (premium with long context)
- WhisperX + GLM 4.6: ~$0.10-0.25 (great for Chinese/multilingual)

## Troubleshooting

### "FFmpeg not found"
Install FFmpeg (see Prerequisites section)

### "OPENAI_API_KEY not found"
Create a `.env` file with your API key (see Installation section)

### "Out of memory" with Whisper
Use a smaller model: `--whisper-model tiny` or `--whisper-model base`

### Video download fails
- Check the URL is valid
- Some videos may be region-locked or private
- Age-restricted videos might not work

### ElevenLabs authentication error
- Get your API key from https://elevenlabs.io
- Add to `.env` file: `ELEVENLABS_API_KEY=your_key_here`
- Restart the application after adding the key

### ElevenLabs quota exceeded
- Check your usage at https://elevenlabs.io/app/usage
- Free tier includes 2.5 hours/month
- Upgrade your plan or switch to Whisper/WhisperX for unlimited free local transcription

### File too large for ElevenLabs
- ElevenLabs has a 3GB file size limit
- Use Whisper or WhisperX for larger files

### WhisperX speaker diarization not working
- Requires HF_TOKEN in `.env` file
- Get token from https://huggingface.co/settings/tokens
- Accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1

## Performance Tips

**Transcription** (rankings backed by `benchmarks/`):
1. **Best free accuracy**: `--engine parakeet` (0% WER on clean wideband in the project corpus)
2. **Free + Speaker ID**: `--engine parakeet-dia` (add `--num-speakers N` or `--auto-speakers` for 3+ speakers)
3. **Degraded/telephony audio**: `--engine whisper` (most robust on awful recordings)
4. **Best speaker counting**: `--engine openai` (9/9 perfect counts unhinted, incl. 5-speaker panels)
5. **99 languages / audio events / word-level bookmarks**: `--engine elevenlabs`

**Summarization:**
1. **Lower costs**: Use `--model gpt-4o-mini` or `--model claude-haiku-4-5-20251001`
2. **Higher quality**: Use `--model claude-sonnet-4-6`
3. **Complex reasoning**: Use `--model gpt-5.1` (latest OpenAI reasoning model)
4. **Long context**: Use `--model openrouter/moonshot/kimi-k2` (200K+ tokens)
5. **Multilingual**: Use `--model openrouter/zhipuai/glm-4.6-plus` (excellent for Chinese)

## Advanced Usage

### Using as a Library

```python
from utils.downloader import YouTubeDownloader
from utils.transcriber import AudioTranscriber
from utils.summarizer import ContentSummarizer

# Download video
downloader = YouTubeDownloader()
video_data = downloader.download_video("https://youtube.com/watch?v=...")

# Transcribe
transcriber = AudioTranscriber(model_name="base")
transcript = transcriber.transcribe(video_data['audio_file'])

# Summarize
summarizer = ContentSummarizer(model="gpt-4o-mini")
summary = summarizer.summarize(transcript['text'], video_data)
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube video downloading
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [OpenAI API](https://openai.com/api/) - Text summarization
