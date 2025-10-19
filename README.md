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
- **Enhanced Audio Transcription**: Uses Whisper AI with optimized prompts for podcast/conversation content
- **Timestamped Markdown Transcripts**: Bold timestamps with proper formatting for easy reading
- **Two Analysis Modes**: Choose between Basic (5 sections) or Advanced (9 sections) summaries
- **External Prompt Files**: Easily customize analysis prompts via markdown files
- **AI-Powered Summaries**: Generates well-formatted summaries with timestamps, quotes, and references
- **Multiple AI Models**: OpenAI (GPT-4o-mini, GPT-4o, GPT-5) and Anthropic (Claude Haiku, Claude Sonnet)
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

3. **Set up your OpenAI API key:**
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add your API key
```

Your `.env` file should look like:
```
OPENAI_API_KEY=sk-your-api-key-here
SUMMARY_MODEL=gpt-4o-mini
WHISPER_MODEL=base
```

## Project Structure

```
Sonopsis/
├── sonopsis.py          # Interactive menu interface (recommended)
├── main.py              # Command-line interface
├── utils/               # Core modules (downloader, transcriber, summarizer)
├── scripts/             # Testing and comparison scripts
├── docs/                # Documentation and analysis prompts
│   ├── analysis_basic.md      # Basic analysis prompt template
│   ├── analysis_advanced.md   # Advanced analysis prompt template
│   ├── QUICKSTART.md          # Quick start guide
│   └── STORAGE.md             # Storage locations info
├── downloads/           # Temporary audio files
├── transcripts/         # Generated markdown transcripts
└── summaries/           # AI summaries
```

## Usage

### Quick Start (Easiest!)

```bash
python ytp.py
```

**Or on Windows:**
```bash
ytp
```

**Or on Linux/Mac:**
```bash
./ytp.sh
```

### Interactive Mode (Recommended)

The short command `ytp` launches the full interactive interface:

**Features:**
- Step-by-step guided interface with beautiful colored menus
- Interactive model selection with descriptions
- Shows already-downloaded Whisper models
- Clear cost and speed information with visual tags
- Process multiple videos in one session

### Command Line Mode

```bash
python main.py <YouTube_URL>
```

### Examples

```bash
# Process a single video with default settings
python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Process an entire playlist
python main.py "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

# Use a larger Whisper model for better accuracy
python main.py https://youtu.be/dQw4w9WgXcQ --whisper-model small

# Use Claude Sonnet for highest quality summaries
python main.py <URL> --gpt-model claude-sonnet-4-5-20250929

# Process playlist with specific models
python main.py <PLAYLIST_URL> --whisper-model base --gpt-model claude-haiku-4-5-20251001

# Keep downloaded audio files
python main.py <URL> --keep-files
```

### Command Line Options

- `url` (required): YouTube video or playlist URL
- `--whisper-model`: Whisper model size - `tiny`, `base`, `small`, `medium`, `large` (default: `base`)
- `--gpt-model`: AI model for summaries (default: `gpt-4o-mini`)
  - OpenAI: `gpt-4o-mini`, `gpt-4o`, `gpt-5`
  - Anthropic Claude: `claude-haiku-4-5-20251001`, `claude-sonnet-4-5-20250929`
- `--keep-files`: Keep downloaded audio files after processing

### Playlist Processing

The tool automatically detects playlist URLs and processes all videos sequentially:

- Extracts all video URLs from the playlist
- Shows a summary before starting (total videos, models, etc.)
- Processes each video one at a time with progress tracking
- Provides a final summary showing successful/failed videos
- All transcripts and summaries are saved individually in their respective folders

### Whisper Model Comparison

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

**OpenAI Whisper:**
- Runs locally (free after initial download)
- First-time model download required

**AI Model Pricing (per 3-hour video):**
- `gpt-4o-mini`: ~$0.05-0.10 (cheapest OpenAI)
- `gpt-4o`: ~$0.15-0.30
- `gpt-5`: ~$0.20-0.40 (best OpenAI reasoning)
- `claude-haiku-4-5`: ~$0.03-0.10 (fastest, cheapest)
- `claude-sonnet-4-5`: ~$0.10-0.30 (best overall quality)

Costs vary based on transcript length. A 10-minute video typically costs $0.01-0.05 with most models.

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

## Performance Tips

1. **Faster processing**: Use `--whisper-model tiny` for quick tests
2. **Better accuracy**: Use `--whisper-model small` or `medium`
3. **Lower costs**: Use `gpt-4o-mini` for summaries
4. **Higher quality**: Use `gpt-4` for summaries

## Advanced Usage

### Using as a Library

```python
from downloader import YouTubeDownloader
from transcriber import AudioTranscriber
from summarizer import ContentSummarizer

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

This project is provided as-is for educational and personal use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube video downloading
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [OpenAI API](https://openai.com/api/) - Text summarization
