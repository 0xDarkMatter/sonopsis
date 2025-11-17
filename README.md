```
███████╗ ██████╗ ███╗   ██╗ ██████╗ ██████╗ ███████╗██╗███████╗
██╔════╝██╔═══██╗████╗  ██║██╔═══██╗██╔══██╗██╔════╝██║██╔════╝
███████╗██║   ██║██╔██╗ ██║██║   ██║██████╔╝███████╗██║███████╗
╚════██║██║   ██║██║╚██╗██║██║   ██║██╔═══╝ ╚════██║██║╚════██║
███████║╚██████╔╝██║ ╚████║╚██████╔╝██║     ███████║██║███████║
╚══════╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝╚══════╝
```

# Sonopsis

**AI-Powered Video/Audio Summarizer** - Download · Transcribe · Analyze

A comprehensive Python application that downloads YouTube videos, transcribes them using multiple AI engines, and generates detailed, intelligent summaries using state-of-the-art language models.

---

## Quick Start (3 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys
Copy `.env.example` to `.env` and add your API keys:
```bash
cp .env.example .env
# Edit .env and add your keys
```

### 3. Run!
```bash
python sonopsis.py
```

The interactive interface will guide you through the rest.

**First time?** Try this:
1. Paste any YouTube URL
2. Select **BASE** Whisper model (recommended, fast)
3. Select **CLAUDE SONNET 4.5** for best quality summaries
4. Wait ~30-60 seconds
5. Check `summaries/` folder for your result!

---

## Features

### Core Capabilities
- **Interactive Menu Interface**: Beautiful Claude Code-style menus with keyboard navigation
- **Download YouTube Videos**: Automatically downloads and extracts audio using yt-dlp
- **Playlist Batch Processing**: Process entire YouTube playlists with progress tracking
- **Smart File Naming**: Videos saved as `YT_{ID}_{Title}` with comprehensive YouTube metadata
- **Two Analysis Modes**: Basic (5 sections) or Advanced (9 sections) summaries
- **Customizable Prompts**: External markdown files for easy prompt customization
- **Streaming Support**: Prevents timeouts on long videos (2+ hours)
- **Model Tracking**: Summaries include which AI models were used for full transparency

### Multiple Transcription Engines

| Engine      | Cost  | Speed      | Languages | Speaker ID | Audio Events | Timestamps | Best For |
|-------------|-------|------------|-----------|------------|--------------|------------|----------|
| **Whisper**     | Free  | Fast       | ~60       | No         | No           | No         | Quick transcription, offline use |
| **WhisperX**    | Free  | Medium     | ~60       | Yes        | No           | No         | Free speaker ID, GPU available |
| **ElevenLabs**  | Paid* | Very Fast  | 99        | Yes (32)   | Yes          | Yes        | Premium quality, 99 languages |

\* ElevenLabs: Free tier includes 2.5 hours/month

#### Speaker Diarization
ElevenLabs and WhisperX support speaker diarization (identifying "who said what"):
- **Automatic speaker detection**: Up to 32 speakers with ElevenLabs
- **Audio events**: ElevenLabs captures `[laughter]`, `[music]`, `[applause]`, etc.
- **YouTube bookmarks**: Clickable timestamps that jump directly to video moments
- **Format**: `**[SPEAKER_00]** [00:01:23] The text spoken...`

### Multiple AI Models

**OpenAI Models:**
- **GPT-4o-mini**: Fastest, cheapest ($0.05/3hrs) - Good for simple content
- **GPT-4o**: Balanced performance ($0.15/3hrs)
- **GPT-5.1**: Latest reasoning model ($0.20/3hrs) - PhD-level analysis, catches transcript errors

**Anthropic Claude Models:**
- **Claude Haiku 4.5**: Best value ($0.03/3hrs) - 90% quality at 1/3 cost
- **Claude Sonnet 4.5**: Best overall quality ($0.10/3hrs) - Default choice ⭐

**OpenRouter Models:**
- **Kimi K2**: Long context specialist ($0.15/3hrs) - 200K+ tokens
- **GLM 4.6 Plus**: Multilingual champion ($0.10/3hrs) - Excellent for Chinese

### Quality & Performance Features
- **Anti-Hallucination System**: Strong prompts prevent fabricated references and citations
- **Elevated Language**: Sophisticated prose for educated audiences
- **Smart Thresholding**: Optimized speaker separation (0.1 threshold for max sensitivity)
- **Token Optimization**: No artificial caps - full context utilization
- **Filename Sanitization**: Unicode → ASCII conversion for cross-platform compatibility

---

## Prerequisites

- **Python 3.8+**
- **FFmpeg** (required for audio processing)
- **API Keys**: At minimum, one of:
  - OpenAI API key (for GPT models)
  - Anthropic API key (for Claude models)

### Installing FFmpeg

**Windows:**
```bash
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

---

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/0xDarkMatter/sonopsis.git
cd sonopsis
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up your API keys:**
```bash
cp .env.example .env
```

Edit `.env` and add your keys:
```env
# Required: At least one AI provider
OPENAI_API_KEY=sk-your-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional: For additional features
ELEVENLABS_API_KEY=your-elevenlabs-key  # Cloud transcription
HF_TOKEN=your-huggingface-token          # WhisperX speaker diarization
OPENROUTER_API_KEY=your-openrouter-key   # Kimi K2, GLM 4.6 models

# Optional: Default model selection
SUMMARY_MODEL=claude-sonnet-4-5-20250929
WHISPER_MODEL=base
WHISPER_CACHE_DIR=/path/to/whisper/cache  # Custom cache location
```

**Getting API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **ElevenLabs**: https://elevenlabs.io (Dashboard → API Keys)
- **Hugging Face**: https://huggingface.co/settings/tokens (also accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1)
- **OpenRouter**: https://openrouter.ai/keys

---

## Usage

### Interactive Mode (Recommended)

```bash
python sonopsis.py
```

**Features:**
- Step-by-step guided interface with colored menus
- Interactive model selection with cost/speed information
- Visual tags: `[RECOMMENDED]`, `[BEST VALUE]`, `[TOP QUALITY]`
- Shows already-downloaded Whisper models
- Analysis mode selection (Basic or Advanced)
- Process multiple videos in one session

### Command Line Mode

```bash
python sonopsis-cli.py <YouTube_URL> [options]
```

### Usage Examples

```bash
# Basic: Single video with defaults (Whisper + Claude Sonnet)
python sonopsis-cli.py https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Process an entire playlist
python sonopsis-cli.py "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

# Use ElevenLabs for speaker diarization + YouTube bookmarks
python sonopsis-cli.py <URL> --transcription-engine elevenlabs

# Use WhisperX for free speaker diarization (GPU recommended)
python sonopsis-cli.py <URL> --transcription-engine whisperx

# Use larger Whisper model for better accuracy
python sonopsis-cli.py <URL> --whisper-model small

# Use Claude Haiku for best value ($0.03/3hrs)
python sonopsis-cli.py <URL> --gpt-model claude-haiku-4-5-20251001

# Use GPT-5.1 for complex reasoning
python sonopsis-cli.py <URL> --gpt-model gpt-5.1

# Use Kimi K2 for long context (200K+ tokens)
python sonopsis-cli.py <URL> --gpt-model openrouter/moonshot/kimi-k2

# Advanced analysis mode (9 sections instead of 5)
python sonopsis-cli.py <URL> --analysis-mode advanced

# Process playlist with ElevenLabs + Claude
python sonopsis-cli.py <PLAYLIST_URL> --transcription-engine elevenlabs --gpt-model claude-sonnet-4-5-20250929

# Keep downloaded audio files (deleted by default)
python sonopsis-cli.py <URL> --keep-files

# Resume playlist from video #5
python sonopsis-cli.py <PLAYLIST_URL> --start-from 5
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `url` | YouTube video or playlist URL | Required |
| `--transcription-engine` | `whisper`, `whisperx`, or `elevenlabs` | `whisper` |
| `--whisper-model` | `tiny`, `base`, `small`, `medium`, `large` | `base` |
| `--gpt-model` | AI model for summaries (see below) | `claude-sonnet-4-5-20250929` |
| `--analysis-mode` | `basic` or `advanced` | `basic` |
| `--keep-files` | Keep downloaded audio files | `False` |
| `--start-from` | Start from video N (playlists only) | `1` |

**Available AI Models:**
- **OpenAI**: `gpt-4o-mini`, `gpt-4o`, `gpt-5.1`
- **Anthropic**: `claude-haiku-4-5-20251001`, `claude-sonnet-4-5-20250929`
- **OpenRouter**: `openrouter/moonshot/kimi-k2`, `openrouter/zhipuai/glm-4.6-plus`

---

## Transcription Engines

### When to Use Each Engine

**Whisper (Local, Free)**
- Quick transcription without speaker identification
- Offline use, no API costs after model download
- ~60 languages supported
- Best for: Simple content, cost-conscious users

**WhisperX (Local, Free)**
- Free speaker diarization (who said what)
- Requires Hugging Face token
- GPU recommended for best performance
- Best for: Interviews/podcasts on a budget

**ElevenLabs (Cloud, Paid)**
- 99 language support
- Up to 32 speaker identification
- Audio events: `[laughter]`, `[music]`, `[applause]`
- YouTube timestamp bookmarks
- Best for: Professional use, non-English content, no GPU

### ElevenLabs YouTube Bookmarks

When using ElevenLabs, timestamps become clickable YouTube links:

**Transcript format:**
```markdown
**[SPEAKER_00]** [00:01:23] We discovered something amazing about...
**[SPEAKER_01]** [00:02:45] That's incredible! Tell me more...
```

**AI summaries can convert to:**
```markdown
The host explains the discovery at [00:01:23](https://youtu.be/VIDEO_ID?t=83s)
The guest responds at [00:02:45](https://youtu.be/VIDEO_ID?t=165s)
```

Perfect for creating navigable, citation-rich summaries!

### Whisper Model Comparison

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny | ~75 MB | Fastest | Good | Quick tests, simple content |
| base | ~150 MB | Fast | Better | **General use (recommended)** |
| small | ~500 MB | Medium | Great | Higher accuracy needed |
| medium | ~1.5 GB | Slow | Excellent | Professional transcription |
| large | ~3 GB | Slowest | Best | Maximum accuracy |

**Models are cached** at `~/.cache/whisper/` (or custom `WHISPER_CACHE_DIR`)

---

## AI Model Performance

Based on extensive testing with real content (15-minute videos):

| Model | Speed | Quality | Cost | Best For |
|-------|-------|---------|------|----------|
| Claude Sonnet 4.5 | 41s | ⭐⭐⭐⭐⭐ | $0.25 | **Best overall** |
| Claude Haiku 4.5 | 31s | ⭐⭐⭐⭐⭐ | $0.08 | **Best value** (90% quality, 1/3 cost) |
| GPT-5.1 | 65s | ⭐⭐⭐⭐⭐ | $0.30 | Error correction, PhD-level reasoning |
| GPT-4o | 28s | ⭐⭐⭐ | $0.15 | Balanced performance |
| GPT-4o-mini | 15s | ⭐⭐ | $0.05 | Speed over quality |
| Kimi K2 | ~45s | ⭐⭐⭐⭐ | $0.20 | Long context (200K+ tokens) |
| GLM 4.6 Plus | ~35s | ⭐⭐⭐⭐ | $0.12 | Multilingual, especially Chinese |

### Cost Examples (3-hour video)

**Budget Options:**
- Whisper + GPT-4o-mini: ~$0.05-0.10
- WhisperX + Claude Haiku: ~$0.03-0.10 (with speaker ID!)

**Balanced:**
- Whisper + Claude Sonnet: ~$0.10-0.30
- ElevenLabs + Claude Haiku: ~$0.70-1.50 (99 languages)

**Premium:**
- ElevenLabs + Claude Sonnet: ~$0.76-1.74 (best quality)
- ElevenLabs + GPT-5.1: ~$0.86-1.84 (PhD-level analysis)

---

## Project Structure

```
Sonopsis/
├── sonopsis.py              # Interactive menu interface (recommended)
├── sonopsis-cli.py          # Command-line interface
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
│
├── utils/                  # Core modules
│   ├── downloader.py       # YouTube download (yt-dlp)
│   ├── transcriber.py      # Audio transcription (Whisper/WhisperX/ElevenLabs)
│   └── summarizer.py       # AI summarization (GPT/Claude/OpenRouter)
│
├── scripts/                # Testing and comparison tools
│   ├── compare_models.py   # Test all models on same video
│   ├── process_existing.py # Process existing audio files
│   └── test_gpt5.py        # GPT-5 specific testing
│
├── docs/                   # Documentation and prompts
│   ├── analysis_basic.md   # Basic analysis prompt (5 sections)
│   ├── analysis_advanced.md # Advanced analysis prompt (9 sections)
│   ├── system_prompt.md    # Core system prompt
│   ├── speaker_identification_protocol.md # Speaker ID workflow
│   ├── QUICKSTART.md       # Quick start guide
│   └── STORAGE.md          # Storage locations
│
├── downloads/              # Downloaded audio files (temp, auto-deleted)
├── transcripts/            # Generated markdown transcripts
└── summaries/              # AI-generated summaries
```

---

## Output Structure

### File Naming Convention
Videos are saved with YouTube ID and sanitized title:
```
YT_{VIDEO_ID}_{Sanitized_Title}_transcript.md
YT_{VIDEO_ID}_{Sanitized_Title}_summary.md
```

Example: `YT_dQw4w9WgXcQ_Rick_Astley_Never_Gonna_Give_You_Up_summary.md`

### Sample Outputs

**Transcript** (`transcripts/YT_{ID}_{Title}_transcript.md`):
```markdown
# Video Transcript

**Video ID:** dQw4w9WgXcQ
**Title:** Rick Astley - Never Gonna Give You Up
**Channel:** Rick Astley
**Duration:** 00:03:32
**Language:** en
**URL:** https://youtube.com/watch?v=dQw4w9WgXcQ

---

## Transcript

**[00:00:00 -> 00:00:15]** We're no strangers to love...

**[00:00:16 -> 00:00:42]** You know the rules and so do I...
```

**With Speaker Diarization** (ElevenLabs/WhisperX):
```markdown
**[SPEAKER_00]** [00:00:15] Welcome to the show, I'm your host...

**[SPEAKER_01]** [00:00:42] Thanks for having me! Today we're discussing...

**[SPEAKER_00]** [00:01:23] [laughs] That's a great point...
```

**Summary** (`summaries/YT_{ID}_{Title}_summary.md`):
```markdown
# Video Summary: Rick Astley - Never Gonna Give You Up

**Video ID:** dQw4w9WgXcQ
**Channel:** Rick Astley
**Duration:** 3m 32s
**URL:** https://youtube.com/watch?v=dQw4w9WgXcQ
**Generated:** 2025-11-15 10:30:00
**Models Used:** Whisper (base), Claude Sonnet 4.5

---

## Executive Summary
A timeless declaration of unwavering commitment and emotional fidelity...

## Key Topics & Main Points
- **Commitment**: Absolute dedication to relationship
- **Loyalty**: Promise never to abandon or deceive
- **Communication**: Understanding unspoken emotional contracts

## Detailed Analysis
### Emotional Framework
The narrative establishes a foundation of mutual understanding...

[continues with detailed analysis]

## Key Quotes & Timestamps
> "Never gonna give you up, never gonna let you down"
> — **[00:00:45]**

## Key Takeaways
1. Commitment requires both emotional presence and active demonstration
2. Trust forms the cornerstone of meaningful relationships
3. Understanding implicit social contracts strengthens bonds

## Actionable Insights
- Prioritize consistent communication in relationships
- Demonstrate commitment through actions, not just words
- Recognize and honor emotional contracts

---

**Processing Information:**
- Transcription Engine: Whisper (base model)
- AI Model: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- Analysis Mode: Basic (5 sections)
- Processing Date: 2025-11-15
```

---

## Advanced Features

### Playlist Processing

The tool automatically detects playlist URLs:
```bash
python sonopsis-cli.py "https://www.youtube.com/playlist?list=..."
```

**Features:**
- Extracts all video URLs from playlist
- Shows summary before starting (total videos, models, etc.)
- Progress tracking: "Processing Video 3/15"
- Individual transcripts and summaries for each video
- Final summary: successful/failed counts
- Resume capability: `--start-from N`

### Custom Analysis Prompts

Edit `docs/analysis_basic.md` or `docs/analysis_advanced.md` to customize:
- Section structure
- Analysis depth
- Output format
- Specific focus areas

The system automatically loads your custom prompts on each run.

### Model Comparison Testing

Compare all AI models on the same video:
```bash
python scripts/compare_models.py
```

Generates side-by-side comparisons for:
- Quality assessment
- Speed benchmarking
- Cost analysis
- Strengths/weaknesses

### Using as a Library

```python
from utils.downloader import YouTubeDownloader
from utils.transcriber import AudioTranscriber
from utils.summarizer import ContentSummarizer

# Download video
downloader = YouTubeDownloader(output_dir="downloads")
video_data = downloader.download_video("https://youtube.com/watch?v=...")

# Transcribe with ElevenLabs
transcriber = AudioTranscriber(
    output_dir="transcripts",
    use_elevenlabs=True,
    elevenlabs_api_key="your_key"
)
transcript_data = transcriber.transcribe(video_data['audio_file'])

# Summarize with Claude Sonnet
summarizer = ContentSummarizer(
    model="claude-sonnet-4-5-20250929",
    analysis_mode="advanced"
)
summary = summarizer.summarize(transcript_data['text'], video_data)
```

---

## Troubleshooting

### Installation Issues

**"FFmpeg not found"**
- Install FFmpeg (see Prerequisites section)
- Verify installation: `ffmpeg -version`

**"OPENAI_API_KEY not found"**
- Create `.env` file from `.env.example`
- Add your API key without quotes
- Restart application

**"Out of memory" with Whisper**
- Use smaller model: `--whisper-model tiny` or `base`
- Close other applications
- Consider cloud transcription: `--transcription-engine elevenlabs`

### Transcription Issues

**Video download fails**
- Check URL is valid and public
- Some videos may be region-locked or age-restricted
- Try updating yt-dlp: `pip install -U yt-dlp`

**ElevenLabs authentication error**
- Get API key from https://elevenlabs.io
- Add to `.env`: `ELEVENLABS_API_KEY=your_key_here`
- Restart application

**ElevenLabs quota exceeded**
- Check usage at https://elevenlabs.io/app/usage
- Free tier: 2.5 hours/month
- Switch to Whisper/WhisperX for unlimited free transcription

**WhisperX speaker diarization not working**
- Add `HF_TOKEN` to `.env`
- Accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1
- GPU recommended for best performance

**Only detecting one speaker (ElevenLabs)**
- Audio may be mixed to mono (common in podcasts)
- Threshold already optimized (0.1 = maximum sensitivity)
- Consider manual speaker mapping if needed

### Summarization Issues

**"Timeout" errors on long videos**
- Streaming is enabled by default (prevents timeouts)
- If still occurring, try smaller chunks or different model

**API rate limits**
- Claude/GPT: Wait 60 seconds and retry
- ElevenLabs: Check your plan limits
- Consider using different model or tier

---

## Performance Tips

### For Best Speed
1. Use ElevenLabs transcription (cloud-based, fastest)
2. Use `gpt-4o-mini` or `claude-haiku-4-5-20251001`
3. Use basic analysis mode
4. Use smaller Whisper models (`tiny`, `base`)

### For Best Quality
1. Use ElevenLabs or large Whisper model
2. Use `claude-sonnet-4-5-20250929` or `gpt-5.1`
3. Use advanced analysis mode
4. Enable speaker diarization

### For Best Value
1. Use WhisperX (free speaker ID)
2. Use `claude-haiku-4-5-20251001` (90% quality, 1/3 cost)
3. Use basic analysis mode
4. GPU recommended for WhisperX

### For 99 Languages
1. Use `--transcription-engine elevenlabs`
2. Automatic language detection
3. Speaker diarization included
4. Audio events captured

---

## Recent Improvements

### v1.0 (November 2025)
- ✅ Comprehensive speaker identification system (up to 32 speakers)
- ✅ YouTube metadata integration: `YT_{ID}_{Title}` file naming
- ✅ Model tracking in summaries for full transparency
- ✅ Streaming support prevents timeout on 2+ hour videos
- ✅ Anti-hallucination system prevents fabricated references
- ✅ Elevated language sophistication for educated audiences
- ✅ Claude Sonnet 4.5 as recommended default
- ✅ ElevenLabs integration with SRT timestamps
- ✅ WhisperX GPU detection and performance warnings
- ✅ Interactive menu system with keyboard navigation
- ✅ Unicode filename sanitization for cross-platform compatibility

### Technical Highlights
- **Speaker Diarization**: Word-level JSON parsing for accurate speaker separation
- **Threshold Optimization**: 0.1 minimum for maximum sensitivity
- **Token Optimization**: No artificial caps, full context utilization
- **Robust Error Handling**: Graceful degradation on API failures

---

## Future Enhancements

Potential additions:
- [ ] Gemini 2.5 Pro support (1M token context)
- [ ] Web interface for easier access
- [ ] Video chapter detection and analysis
- [ ] Multiple language output (translate summaries)
- [ ] Export formats (PDF, DOCX, HTML)
- [ ] Context-based speaker name identification
- [ ] Batch video comparison analysis
- [ ] Custom section templates
- [ ] Real-time transcription for live streams

---

## Technical Stack

- **YouTube Download**: [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **Audio Processing**: FFmpeg
- **Transcription**:
  - [OpenAI Whisper](https://github.com/openai/whisper) (local)
  - [WhisperX](https://github.com/m-bain/whisperX) (local + diarization)
  - [ElevenLabs API](https://elevenlabs.io) (cloud)
- **Summarization**:
  - [OpenAI API](https://platform.openai.com) (GPT models)
  - [Anthropic API](https://console.anthropic.com) (Claude models)
  - [OpenRouter](https://openrouter.ai) (Kimi K2, GLM 4.6)
- **UI**: Colorama (terminal colors)
- **Config**: python-dotenv

---

## Storage Locations

**Default paths:**
- **Whisper Models**: `~/.cache/whisper/` (customizable via `WHISPER_CACHE_DIR`)
- **Downloads**: `./downloads/` (deleted unless `--keep-files`)
- **Transcripts**: `./transcripts/`
- **Summaries**: `./summaries/`

**Disk space:**
- Whisper base model: ~150 MB
- Whisper large model: ~3 GB
- Temporary audio: Varies by video length (auto-deleted)

---

## Contributing

Contributions are welcome! Areas for improvement:
- Additional AI model support
- Enhanced speaker identification
- UI/UX improvements
- Performance optimizations
- Documentation enhancements

**How to contribute:**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## License

This project is provided as-is for educational and personal use.

**API Services:**
- OpenAI, Anthropic, ElevenLabs, OpenRouter: Subject to their respective terms of service
- Whisper, WhisperX: Open source, see their licenses

---

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Reliable YouTube downloading
- [OpenAI Whisper](https://github.com/openai/whisper) - Revolutionary speech recognition
- [WhisperX](https://github.com/m-bain/whisperX) - Enhanced Whisper with diarization
- [ElevenLabs](https://elevenlabs.io) - Premium transcription service
- [Anthropic Claude](https://www.anthropic.com) - Industry-leading AI reasoning
- [OpenAI](https://openai.com) - GPT models and API
- [OpenRouter](https://openrouter.ai) - Unified LLM access

---

## Support

- **Issues**: https://github.com/0xDarkMatter/sonopsis/issues
- **Documentation**: See `docs/` folder
- **Quick Start**: `docs/QUICKSTART.md`
- **Storage Info**: `docs/STORAGE.md`

**Ready to start?**
```bash
python sonopsis.py
```

Enjoy! 🎉
