# Quick Start Guide

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up API keys:**
Create a `.env` file in the root directory:
```bash
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Usage Options

### 1. Quick Launch (Easiest!)

```bash
python ytp.py
```

**Or simply:**
- Windows: `ytp`
- Linux/Mac: `./ytp.sh`

### 2. Interactive Mode (Recommended for Beginners)

Same as above - `ytp` launches the interactive interface with:
- Beautiful colored menus
- Visual tags ([RECOMMENDED], [BEST VALUE], etc.)
- Cache status indicators

**Features:**
- ✅ Step-by-step guided interface
- ✅ Interactive model selection with descriptions
- ✅ Shows which models are already downloaded
- ✅ Clear cost and speed information
- ✅ Process multiple videos in one session

**Best for:** First-time users, testing different models

---

### 3. Command Line Mode (For Scripts/Automation)

```bash
python main.py <YouTube_URL_or_Playlist> [options]
```

**Examples:**
```bash
# Basic usage - single video (defaults: base whisper, gpt-4o-mini)
python main.py https://www.youtube.com/watch?v=FwpEk-fhZjY

# Process entire playlist
python main.py "https://www.youtube.com/playlist?list=PLxxxxxxx"

# Use Claude Sonnet 4.5 for best quality
python main.py <URL> --gpt-model claude-sonnet-4-5-20250929

# Use small Whisper model for better accuracy
python main.py <URL> --whisper-model small

# Process playlist with specific models
python main.py <PLAYLIST_URL> --whisper-model base --gpt-model claude-haiku-4-5-20251001

# Keep audio files after processing
python main.py <URL> --keep-files
```

**Playlist Processing:**
- Automatically detected from URL (contains "playlist" or "list=")
- Shows video count and confirmation before starting
- Progress tracking for each video (X/Y)
- Final summary with success/failure counts

**Options:**
- `--whisper-model` - tiny, base, small, medium, large (default: base)
- `--gpt-model` - Any supported model (default: gpt-4o-mini)
- `--keep-files` - Don't delete audio after processing

**Best for:** Automation, batch processing, scripts

---

## Model Recommendations

### For Speed (< 20 seconds for 15min video)
```bash
python interactive.py
# Select: gpt-4o-mini + tiny/base whisper
```

### For Quality (Best summaries)
```bash
python interactive.py
# Select: Claude Sonnet 4.5 + small whisper
```

### For Value (Best quality/cost ratio)
```bash
python interactive.py
# Select: Claude Haiku 4.5 + base whisper
```

### For Error Correction (Catches transcript mistakes)
```bash
python interactive.py
# Select: GPT-5 + medium whisper
```

---

## Advanced Usage

### Compare Multiple Models

Compare all available models on the same video:

```bash
python scripts/compare_models.py
```

Edit the script to change which video to analyze.

### Process Existing Audio

If you already have an audio file downloaded:

```bash
python scripts/process_existing.py
```

### Test Specific Model

```bash
python scripts/test_gpt5.py
```

---

## Output Files

After processing, you'll find:

```
transcripts/
  {video_title}_transcript.json  # Full transcript with timestamps
  {video_title}_transcript.txt   # Plain text

summaries/
  {video_title}_summary.md       # Formatted summary
```

---

## Troubleshooting

### FFmpeg not found
```bash
# Windows (Chocolatey)
choco install ffmpeg

# Mac
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### API Key errors
Check your `.env` file has the correct keys without quotes.

### Out of memory (Whisper)
Use a smaller model:
```bash
python main.py <URL> --whisper-model tiny
```

### Slow processing
- Use `tiny` or `base` Whisper models
- Use `gpt-4o-mini` or `claude-haiku-4-5` for summaries

---

## Need Help?

- See full documentation: `README.md`
- Storage information: `docs/STORAGE.md`
- Report issues: https://github.com/anthropics/claude-code/issues
