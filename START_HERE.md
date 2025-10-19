# 🚀 START HERE - Sonopsis

## Super Quick Start (3 steps!)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Add Your API Keys
Create `.env` file (copy from `.env.example`):
```bash
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
```

### 3. Run!
```bash
python ytp.py
```

**Or on Windows, just type:**
```bash
ytp
```

That's it! The interactive interface will guide you through everything else.

---

## What Commands Can I Use?

### **Easiest: Interactive Mode**
```bash
python ytp.py          # Full interactive experience
ytp                    # Windows shortcut
./ytp.sh               # Linux/Mac shortcut
```

### **Quick: Command Line**
```bash
python main.py <YOUTUBE_URL>
```

### **Advanced: Model Comparison**
```bash
python scripts/compare_models.py
```

---

## First Time? Try This:

1. Run `python ytp.py`
2. Paste any YouTube URL or Playlist URL
3. Select **[2] BASE** Whisper model (recommended, fast)
4. Select **[4] CLAUDE HAIKU 4.5** [BEST VALUE] for summary
5. Wait ~30-60 seconds
6. Check the `summaries/` folder for your result!

**Playlist Processing:**
- Just paste a playlist URL and the tool automatically detects it
- You'll see a summary of all videos before processing
- Each video is processed one at a time with progress tracking

---

## Where Are My Files?

- **Transcripts:** `transcripts/` folder
- **Summaries:** `summaries/` folder
- **Whisper Models:** `E:\Coding\WhisperCache\` (not C: drive!)

---

## Need Help?

- **Quick Guide:** `docs/QUICKSTART.md`
- **Full README:** `README.md`
- **Storage Info:** `docs/STORAGE.md`
- **Project Overview:** `PROJECT_SUMMARY.md`

---

## Recommended Models

**For Most Videos:**
- Whisper: **BASE** [RECOMMENDED]
- Summary: **CLAUDE HAIKU 4.5** [BEST VALUE]
- Cost: ~$0.08 for 3-hour video
- Time: ~30 seconds for 15-min video

**For Best Quality:**
- Whisper: **SMALL**
- Summary: **CLAUDE SONNET 4.5** [TOP QUALITY]
- Cost: ~$0.25 for 3-hour video
- Time: ~45 seconds for 15-min video

---

## Common Issues

**"FFmpeg not found"**
```bash
choco install ffmpeg    # Windows
brew install ffmpeg     # Mac
```

**"API key not found"**
- Check your `.env` file exists
- Make sure keys don't have quotes around them

**Want to change Whisper cache location?**
- Edit `WHISPER_CACHE_DIR` in `.env` file

---

**Ready to start? Just run:**
```bash
python ytp.py
```

🎉 Enjoy!
