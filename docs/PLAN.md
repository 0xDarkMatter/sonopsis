# Sonopsis Development Plan

## Recent Changes

### v1.1.0 - Project Structure (2026-01)
- [x] Added `AGENTS.md` for AI assistant instructions
- [x] Reorganized LLM artifacts into `prose/` directory
- [x] Added `config.yaml` for non-secret configuration
- [x] Enhanced `.gitignore` for outputs and caches
- [x] Added `.claude/session-handoff.md` template

## Future Enhancements

### AI & Model Support
- [ ] Gemini 3.0 Pro support
- [ ] Local LLM support (Ollama, llama.cpp)
- [ ] Model comparison mode (run same transcript through multiple models)

### Processing Features
- [ ] Video chapter detection and section-aware summaries
- [ ] Multiple language output (translate summaries)
- [ ] Parallel batch processing for playlists
- [ ] Resume interrupted playlist processing

### Export & Output
- [ ] Export to PDF, DOCX formats
- [ ] Custom summary templates in `prose/templates/`
- [ ] Configurable output formats via `config.yaml`

### Infrastructure
- [ ] Add test suite (`tests/`)
- [ ] CI/CD pipeline for releases
- [ ] Docker container for easy deployment
