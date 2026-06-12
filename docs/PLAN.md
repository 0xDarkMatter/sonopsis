# Sonopsis Development Plan

## Recent Changes

### v0.2.0 - Engines and evidence (2026-06)
- [x] Claude Code CLI summarization backend (subscription, no API key)
- [x] NVIDIA Parakeet engine via onnx-asr - new local default, benchmark-proven
- [x] Local speaker diarization (`parakeet-dia` = Parakeet + pyannote)
- [x] OpenAI gpt-4o-transcribe-diarize engine
- [x] `--num-speakers` / `--auto-speakers` speaker-count controls
- [x] Benchmark suite: WER + DER rubrics, exact-reference corpora, committed results
- [x] Silence-aligned long-audio chunking (eliminates boundary errors)
- [x] Test suite expansion (44 -> 127 unit tests + gated e2e)
- [x] `config.yaml` actually loaded; shared pipeline; model registry
- [x] Resume interrupted playlist processing (`--skip-existing`)
- [x] Optional-extra installs keep core ~50MB

### v1.1.0 - Project Structure (2026-01)
- [x] Added `AGENTS.md` for AI assistant instructions
- [x] Reorganized LLM artifacts into `prose/` directory
- [x] Added `config.yaml` for non-secret configuration
- [x] Enhanced `.gitignore` for outputs and caches

## Future Enhancements

### AI & Model Support
- [ ] Gemini support (Gemini Flash audio is also a cheap STT option worth benchmarking)
- [ ] Local LLM support (Ollama, llama.cpp)
- [ ] Qwen3-ASR / Canary local engines (heavier extras; benchmark first)

### Processing Features
- [ ] Transcript chunking / map-reduce summarization for inputs beyond model context
- [ ] Video chapter detection and section-aware summaries
- [ ] Multiple language output (translate summaries)
- [ ] Parallel batch processing for playlists
- [ ] `--summarize-only` flag to re-summarize an existing transcript

### Speaker Diarization
- [ ] Expand `--auto-speakers` eval to ~25 cases (guest-variant panels) before default-on
- [ ] Overlap-heavy and real-podcast samples in the diarization corpus
- [ ] NVIDIA Sortformer if an ONNX export ships (judge with the existing DER harness)

### Export & Output
- [ ] Export to PDF, DOCX formats
- [ ] Custom summary templates in `prose/templates/`

### Infrastructure
- [ ] CI/CD pipeline for releases
- [ ] Docker container for easy deployment
