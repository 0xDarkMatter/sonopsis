# Engine Selection

Measured on the project's exact-reference corpora (see `benchmarks/` in the
sonopsis repo). WER = word error rate; DER = diarization error rate.

## Decision matrix

| Situation | Engine | Evidence |
|---|---|---|
| Default / best free accuracy | `parakeet` | 0% WER clean wideband (Whisper: 3-20%) |
| 1-2 speakers, want labels, free | `parakeet-dia` + `--num-speakers 2` | 10.3% DER, beat ElevenLabs |
| 3-5+ speaker panel | `openai` | 9/9 perfect speaker counts unhinted, 6-12% DER |
| Heavy crosstalk | `parakeet-dia` | 9.0% DER vs ElevenLabs 15.0% on 1s overlap |
| Degraded/telephony audio | `whisper` | Only engine robust on pathological recordings |
| Word-level timestamps / YouTube bookmark links | `elevenlabs` | Scribe v2; ~0% WER; 2.5h/mo free |
| Non-European languages | `elevenlabs` | 99 languages (parakeet: 25 European) |
| Nothing installed locally | `openai` or `elevenlabs` | Cloud-only |

## Speaker-count hints (diarizing engines)

- Exact `--num-speakers N` is the strongest accuracy lever: it recovered every
  missed speaker in the sweep (e.g. 4-speaker: 22.7% -> 16.9% DER, 3/4 -> 4/4).
- A WRONG count actively hurts (forced phantom speakers double DER) - only
  hint when the count is known.
- `--auto-speakers` infers the count from video metadata via an LLM and applies
  it only at high confidence (validated 5/5 correct, 0 harmful); it abstains on
  music and ambiguous formats, falling back to unhinted diarization.

## Costs

| Engine | Cost | First-run download |
|---|---|---|
| parakeet / parakeet-dia / whisper / whisperx | free | 0.7-2.5GB models |
| elevenlabs | $0.22/audio-hour after 2.5h/month free | none |
| openai | $0.36/audio-hour | none |

Summarization: `claude-cli` is $0 on a Claude subscription; API models run
roughly $0.05-0.80 per 3-hour video depending on tier.
