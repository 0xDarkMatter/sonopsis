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

A Python application that downloads YouTube videos, transcribes them using OpenAI's Whisper, and generates comprehensive summaries and notes using GPT/Claude models.

## Features

- **Interactive Menu Interface**: Beautiful Claude Code-style menus with keyboard navigation
- **Download YouTube Videos**: Automatically downloads videos and extracts audio
- **Playlist Batch Processing**: Process entire YouTube playlists with one command
- **Multiple Transcription Engines**:
  - **Whisper**: Local transcription (free, no speaker labels)
  - **WhisperX**: Local with speaker diarization (free, requires HF token)
  - **ElevenLabs**: Cloud transcription (paid, 99 languages, speaker diarization + audio events)
- **YouTube Bookmark Links**: ElevenLabs transcripts include clickable timestamps that jump to exact moments in the video
- **Two Analysis Modes**: Choose between Basic (5 sections) or Advanced (9 sections) summaries
- **External Prompt Files**: Easily customize analysis prompts via markdown files
- **AI-Powered Summaries**: Generates well-formatted summaries with timestamps, quotes, and references
- **Multiple AI Models**:
  - OpenAI: GPT-4o-mini, GPT-4o, GPT-5.1
  - Anthropic: Claude Haiku 4.5, Claude Sonnet 4.5
  - OpenRouter: Kimi K2, GLM 4.6
- **Customizable Whisper Models**: Choose from tiny, base, small, medium, or large models
- **Progress Tracking**: Real-time progress updates for batch processing

## Prerequisites

- Python 3.8 or higher
- FFmpeg (required for audio processing)
- OpenAI API key

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

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

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
├── requirements.txt         # Python dependencies
├── .env.example             # API key template
├── LICENSE                  # MIT license
├── utils/                   # Core modules
│   ├── downloader.py        # YouTube video/audio download
│   ├── transcriber.py       # Whisper/WhisperX/ElevenLabs transcription
│   └── summarizer.py        # GPT/Claude/OpenRouter summarization
├── scripts/                 # Utility scripts
│   ├── compare_models.py    # Compare AI model outputs
│   └── process_existing.py  # Process existing transcripts
├── docs/                    # Documentation
│   ├── analysis_basic.md    # Basic analysis prompt
│   ├── analysis_advanced.md # Advanced analysis prompt
│   ├── system_prompt.md     # AI system prompt
│   ├── QUICKSTART.md        # Quick start guide
│   └── STORAGE.md           # Storage info
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

# Process an entire playlist
python main.py "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

# Use WhisperX for speaker diarization (local, free)
python main.py <URL> --transcription-engine whisperx

# Use ElevenLabs for cloud transcription (99 languages, speaker diarization)
python main.py <URL> --transcription-engine elevenlabs

# Use a larger Whisper model for better accuracy
python main.py https://youtu.be/dQw4w9WgXcQ --whisper-model small

# Use Claude Sonnet for highest quality summaries
python main.py <URL> --gpt-model claude-sonnet-4-5-20250929

# Use GPT-5.1 for complex reasoning
python main.py <URL> --gpt-model gpt-5.1

# Use Kimi K2 (long context specialist via OpenRouter)
python main.py <URL> --gpt-model openrouter/moonshot/kimi-k2

# Use GLM 4.6 Plus (Chinese + multilingual via OpenRouter)
python main.py <URL> --gpt-model openrouter/zhipuai/glm-4.6-plus

# Process playlist with ElevenLabs transcription and Claude
python main.py <PLAYLIST_URL> --transcription-engine elevenlabs --gpt-model claude-haiku-4-5-20251001

# Keep downloaded audio files
python main.py <URL> --keep-files
```

### Command Line Options

- `url` (required): YouTube video or playlist URL
- `--transcription-engine`: Transcription engine to use (default: `whisper`)
  - `whisper`: Local transcription, free, no speaker labels
  - `whisperx`: Local with speaker diarization, free (requires HF_TOKEN)
  - `elevenlabs`: Cloud transcription, paid, 99 languages, speaker diarization + audio events
- `--whisper-model`: Whisper model size - `tiny`, `base`, `small`, `medium`, `large` (default: `base`)
  - Only applies to `whisper` and `whisperx` engines
- `--gpt-model`: AI model for summaries (default: `claude-sonnet-4-5-20250929`)
  - OpenAI: `gpt-4o-mini`, `gpt-4o`, `gpt-5.1`
  - Anthropic Claude: `claude-haiku-4-5-20251001`, `claude-sonnet-4-5-20250929`
  - OpenRouter: `openrouter/moonshot/kimi-k2`, `openrouter/zhipuai/glm-4.6-plus`
- `--analysis-mode`: Analysis mode - `basic` or `advanced` (default: `basic`)
- `--keep-files`: Keep downloaded audio files after processing
- `--start-from`: Start processing from video number (for playlists, default: 1)

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
| Whisper     | Free  | Fast       | ~60       | No         | No           | No         | Best for quick, simple transcription |
| WhisperX    | Free  | Medium     | ~60       | Yes        | No           | No         | Requires HF token, GPU recommended |
| ElevenLabs  | Paid* | Very Fast  | 99        | Yes (32)   | Yes          | Yes        | Cloud-based, YouTube bookmarks  |

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

### downloader.py
Downloads YouTube videos and extracts audio using yt-dlp.

**Key Functions:**
- `download_video(url, audio_only=True)`: Downloads video/audio
- `get_video_info(url)`: Gets metadata without downloading

### transcriber.py
Transcribes audio files using OpenAI's Whisper model.

**Key Functions:**
- `transcribe(audio_file, language=None)`: Transcribes audio to text
- `transcribe_with_timestamps(audio_file)`: Creates timestamped transcript

### summarizer.py
Generates summaries using OpenAI's GPT models.

**Key Functions:**
- `summarize(transcript, video_metadata)`: Creates comprehensive summary

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
- `claude-sonnet-4-5`: ~$0.10-0.30 (best overall quality)
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

**Transcription:**
1. **Fastest**: Use `--transcription-engine elevenlabs` (cloud, requires API key)
2. **Free + Fast**: Use `--whisper-model tiny` or `--whisper-model base`
3. **Free + Speaker ID**: Use `--transcription-engine whisperx` (requires HF token, GPU recommended)
4. **Best accuracy**: Use `--transcription-engine elevenlabs` or `--whisper-model large`
5. **99 languages**: Use `--transcription-engine elevenlabs`

**Summarization:**
1. **Lower costs**: Use `--gpt-model gpt-4o-mini` or `--gpt-model claude-haiku-4-5-20251001`
2. **Higher quality**: Use `--gpt-model claude-sonnet-4-5-20250929`
3. **Complex reasoning**: Use `--gpt-model gpt-5.1` (latest OpenAI reasoning model)
4. **Long context**: Use `--gpt-model openrouter/moonshot/kimi-k2` (200K+ tokens)
5. **Multilingual**: Use `--gpt-model openrouter/zhipuai/glm-4.6-plus` (excellent for Chinese)

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
