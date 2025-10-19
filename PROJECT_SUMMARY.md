# Sonopsis - Project Summary

## What We Built

A comprehensive Python application that downloads YouTube videos, transcribes them using Whisper AI, and generates high-quality summaries using state-of-the-art AI models (GPT-5, Claude 4.5).

---

## Key Features

### 1. **Interactive Mode** (`interactive.py`)
- User-friendly menu system
- Step-by-step guided workflow
- Real-time model selection with descriptions
- Shows cached Whisper models
- Cost and speed information
- Multi-video processing in one session

### 2. **Multiple AI Model Support**

**OpenAI Models:**
- GPT-4o-mini (fastest, cheapest)
- GPT-4o (balanced)
- GPT-5 (PhD-level reasoning, catches transcript errors)

**Anthropic Claude Models:**
- Claude Haiku 4.5 (best value - 90% quality at 1/3 cost)
- Claude Sonnet 4.5 (best overall quality)

### 3. **Whisper Transcription**
- 5 model sizes (tiny to large)
- Automatic language detection
- Timestamped transcripts
- Local processing (free after download)

### 4. **Quality Comparison Tools**
- `scripts/compare_models.py` - Test all models on same video
- Side-by-side quality analysis
- Performance benchmarking

---

## Project Organization

```
Sonopsis/
├── main.py              # CLI interface
├── interactive.py       # Interactive menu (NEW!)
├── utils/              # Core modules
│   ├── downloader.py
│   ├── transcriber.py
│   └── summarizer.py
├── scripts/            # Testing tools
│   ├── compare_models.py
│   ├── process_existing.py
│   └── test_gpt5.py
├── docs/               # Documentation
│   ├── QUICKSTART.md
│   └── STORAGE.md
└── [outputs]           # downloads/, transcripts/, summaries/
```

---

## Model Performance (15-min video test)

| Model | Speed | Quality | Cost | Best For |
|-------|-------|---------|------|----------|
| Claude Sonnet 4.5 | 41s | ⭐⭐⭐⭐⭐ | $0.25 | Best overall |
| Claude Haiku 4.5 | 31s | ⭐⭐⭐⭐⭐ | $0.08 | **Best value** |
| GPT-5 | 65s | ⭐⭐⭐⭐⭐ | $0.30 | Error correction |
| GPT-4o | 28s | ⭐⭐⭐ | $0.15 | Balanced |
| GPT-4o-mini | 15s | ⭐⭐ | $0.05 | Speed |

---

## Key Achievements

### ✅ Model Support
- Added full Claude 4.5 support (Haiku & Sonnet)
- Fixed GPT-5 integration (special parameters)
- Support for 5 Whisper models

### ✅ User Experience
- Created interactive mode with guided workflow
- Clear model selection with cost/speed info
- Shows cached models to avoid re-downloads

### ✅ Code Organization
- Separated core modules (`utils/`)
- Organized testing scripts (`scripts/`)
- Created comprehensive documentation (`docs/`)

### ✅ Quality Testing
- Extensive model comparisons on real content
- Identified Claude Haiku 4.5 as best value
- Claude Sonnet 4.5 as quality leader
- GPT-5 for error correction

### ✅ Documentation
- Quick start guide
- Storage location documentation
- Updated README with new structure

---

## Storage Locations

**Whisper Models:** `~/.cache/whisper/` (139 MB for base model)
**Outputs:** `./transcripts/`, `./summaries/`
**Audio:** `./downloads/` (auto-deleted unless --keep-files)

---

## Recommendations

### For 2-3 Hour Videos:

**Default Choice:**
```bash
python interactive.py
# Select: Claude Haiku 4.5 + base Whisper
# Cost: ~$0.08, Time: ~30s per 15min
```

**Maximum Quality:**
```bash
# Select: Claude Sonnet 4.5 + small Whisper
# Cost: ~$0.25, Time: ~45s per 15min
```

**Error Correction:**
```bash
# Select: GPT-5 + medium Whisper
# Cost: ~$0.35, Time: ~75s per 15min
```

---

## Future Enhancements

Potential additions:
- [ ] Gemini 2.5 Pro support (1M token context)
- [ ] Batch processing multiple videos
- [ ] Web interface
- [ ] Video chapter detection
- [ ] Multiple language output
- [ ] Export to other formats (PDF, DOCX)

---

## Technical Stack

- **YouTube Download:** yt-dlp
- **Audio Processing:** FFmpeg
- **Transcription:** OpenAI Whisper (local)
- **Summarization:** OpenAI API, Anthropic API
- **UI:** Colorama (terminal colors)
- **Config:** python-dotenv

---

## Quick Start

1. Install: `pip install -r requirements.txt`
2. Add API keys to `.env`
3. Run: `python interactive.py`
4. Follow prompts!

See `docs/QUICKSTART.md` for detailed instructions.
