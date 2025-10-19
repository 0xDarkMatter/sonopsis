# Storage Locations

This document describes where different files and models are stored in the Sonopsis project.

## Project Directories

```
Sonopsis/
├── downloads/          # Downloaded audio files (temporary unless --keep-files)
├── transcripts/        # Generated transcripts (JSON and TXT formats)
├── summaries/          # AI-generated summaries (Markdown format)
├── utils/              # Core utility modules
├── scripts/            # Testing and comparison scripts
├── docs/               # Documentation files
└── .env                # API keys and configuration (not in git)
```

## Whisper Model Storage

Whisper models are stored in a custom location to avoid using C: drive space:

**Location:** `E:\Coding\WhisperCache\` (configurable via WHISPER_CACHE_DIR in .env)

### Model Sizes:
- `tiny.pt` - ~75 MB
- `base.pt` - ~150 MB (currently downloaded)
- `small.pt` - ~500 MB
- `medium.pt` - ~1.5 GB
- `large.pt` - ~3 GB

### Benefits of Custom Location:
- ✅ **Saves C: drive space** - No models stored on system drive
- ✅ **Shared across projects** - All Python projects can use the same cache
- ✅ **Customizable** - Change location via WHISPER_CACHE_DIR environment variable
- ✅ **Models downloaded once** - Reused for all future transcriptions

### Changing Cache Location:
Edit `.env` file:
```bash
WHISPER_CACHE_DIR=E:/Coding/WhisperCache  # or any other path
```

**Note:** Models are downloaded only once and reused for all future transcriptions.

## Output File Naming

### Transcripts
- **JSON:** `{video_title}_transcript.json` - Full transcript with timestamps
- **TXT:** `{video_title}_transcript.txt` - Plain text transcript

### Summaries
- **Markdown:** `{video_title}_summary.md` - Formatted summary with metadata

### Model Comparisons
When using `scripts/compare_models.py`:
- `summaries/comparison_{model_name}/{video_title}_summary.md`

## Cleaning Up

### Remove Downloaded Audio
Audio files are automatically deleted after processing unless you use:
- `--keep-files` flag with `main.py`
- Answer "y" to keep files in `interactive.py`

### Clear Whisper Cache
To free up disk space from unused Whisper models:
```bash
# Windows
rd /s /q E:\Coding\WhisperCache

# Linux/Mac (if using custom path)
rm -rf /path/to/your/WhisperCache
```

Models will be re-downloaded when needed.

### Freed C: Drive Space
By moving Whisper models to E: drive, you've freed up 139 MB from C: drive (with base model). If you download all models, you'll save up to 5.3 GB on C: drive!

### Clear Output Files
```bash
# Remove all transcripts
rm -rf transcripts/*

# Remove all summaries
rm -rf summaries/*

# Remove all downloads
rm -rf downloads/*
```

## API Key Storage

API keys are stored in the `.env` file in the root directory:
- `OPENAI_API_KEY` - For GPT models and Whisper (local doesn't need this)
- `ANTHROPIC_API_KEY` - For Claude models

**Security:** The `.env` file is excluded from git via `.gitignore`
