# Speaker Diarization Implementation Plan

## Current Status

### ✅ What's Working
1. **ElevenLabs Integration**: Successfully integrated Scribe V2 API
2. **Timestamp Preservation**: SRT format provides accurate timestamps
3. **Audio Events**: Tags like `[laughter]`, `[music]`, `[applause]` are captured
4. **Token Optimization**: Removed artificial caps (Claude: 64K, OpenAI: unlimited)
5. **Streaming**: Enabled for long videos (prevents timeout)
6. **Anti-Hallucination**: Strong warnings prevent fabricated references
7. **Language Sophistication**: Elevated prose quality for educated audience
8. **Filename Sanitization**: Unicode → ASCII conversion

### ❌ What's Not Working
**Speaker Diarization**: Only detecting `speaker_0` despite:
- Correct API parameters (`diarize: True`, `diarization_threshold: 0.1`)
- Requesting both SRT and segmented_json formats
- Multiple distinct speakers in test videos (Jeremy Corbell, Dr. Lacatski, George Knapp, Dylan Borland)

## Root Cause Discovery

### **Key Finding: SRT vs segmented_json**

**SRT Format** (what we're currently parsing):
```srt
1
00:00:00,100 --> 00:00:11,700
[suspenseful music]

2
00:00:11,760 --> 00:00:14,760
I get this email on the Navy's secret network
```
❌ **NO speaker labels in SRT output**

**segmented_json Format** (what we need to parse):
```json
{
  "segments": [{
    "text": "...",
    "words": [
      {"text": "I", "start": 11.76, "end": 11.82, "type": "word", "speaker_id": "speaker_0"},
      {"text": " ", "start": 11.82, "end": 11.9, "type": "spacing", "speaker_id": "speaker_0"},
      {"text": "get", "start": 11.9, "end": 12.02, "type": "word", "speaker_id": "speaker_0"}
    ]
  }]
}
```
✅ **HAS speaker_id for each word**

### **Why Only One Speaker Detected?**

Two possibilities:
1. **Audio Mixing**: Podcast/interview audio is mixed to mono or processed in a way that makes voices acoustically similar
2. **Threshold Too High**: Even at 0.1 (minimum), the algorithm isn't separating speakers

**Evidence**:
- All test videos have multiple speakers
- All videos show `speaker_0` only in segmented_json
- Threshold has been lowered from 0.22 → 0.15 → 0.1 with no improvement

## Implementation Plan

### Phase 1: Parse segmented_json Properly ✨ PRIORITY

**File**: `utils/transcriber.py`

**Current code** (lines 515-584):
- Parses SRT format
- Looks for `[SPEAKER_XX]` tags in text (they don't exist)
- Groups by speaker

**Needed code**:
```python
# Parse segmented_json for speaker labels
import json
json_data = json.loads(json_format.content)

# Extract words with speaker_id and timestamps
segments_by_speaker = []
current_speaker = None
current_words = []
current_start = None

for segment in json_data.get('segments', []):
    for word in segment.get('words', []):
        if word['type'] != 'word' and word['type'] != 'audio_event':
            continue

        speaker = word['speaker_id']

        # New speaker or first word
        if speaker != current_speaker:
            if current_words:
                # Save previous segment
                segments_by_speaker.append({
                    'speaker': current_speaker,
                    'start': current_start,
                    'text': ''.join(current_words)
                })
            current_speaker = speaker
            current_words = [word['text']]
            current_start = word['start']
        else:
            current_words.append(word['text'])

# Format output
for seg in segments_by_speaker:
    timestamp = format_timestamp(seg['start'])
    transcript_lines.append(
        f"**[{seg['speaker'].upper()}]** `[{timestamp}]` {seg['text']}\n"
    )
```

### Phase 2: Test with Known Multi-Speaker Content

**Test Videos**:
1. ✅ Already tested: Dylan Borland interview (Jeremy + Dylan + George Knapp)
2. ✅ Already tested: Dr. Lacatski interview (Jeremy + Dr. Lacatski + George Knapp)
3. 🆕 Suggested: News interview with clear audio separation
4. 🆕 Suggested: Debate with back-and-forth dialogue

**Expected Outcomes**:
- If threshold=0.1 works: Should see `speaker_0`, `speaker_1`, `speaker_2`
- If still only `speaker_0`: Audio mixing issue - may need manual speaker identification

### Phase 3: Fallback Strategy if Diarization Fails

**Option A: Context-Based Speaker Identification**
- Use video title, channel name, description
- Pattern matching for dialogue cues ("Jeremy:", "George:", etc.)
- Manual mapping: `speaker_0` → `[Jeremy Corbell]`

**Option B: Post-Processing**
- Save raw `speaker_X` labels
- Provide user option to map speakers manually
- Update transcript with actual names

**Option C: Alternative Service**
- Test AssemblyAI speaker diarization
- Test Deepgram speaker diarization
- Compare quality with ElevenLabs

### Phase 4: Documentation & User Guidance

**README.md updates**:
- Explain speaker diarization limitations
- Document when it works vs. doesn't
- Provide troubleshooting steps

**Known Limitations**:
- Podcast/interview audio with mono mixing may show single speaker
- ElevenLabs detects voices acoustically, not semantically
- `diarization_threshold` range: 0.1 (sensitive) to 0.4 (conservative)

## Technical Debt to Clean Up

1. **Remove debug logging** from `utils/transcriber.py` (lines 472-520)
2. **Remove unused SRT parsing** once JSON parsing works
3. **Update comments** to reflect segmented_json is the source of truth
4. **Add error handling** for missing speaker_id in JSON

## Success Criteria

✅ **Minimum Viable**:
- Parse segmented_json correctly
- Extract speaker_id from each word
- Group by speaker and preserve timestamps
- Format as: `**[SPEAKER_0]** `[HH:MM:SS]` text...`

✅ **Ideal**:
- Detect 2-3+ speakers in multi-speaker videos
- Threshold=0.1 effectively separates voices
- AI can infer speaker names from context

✅ **Acceptable Fallback**:
- Single speaker detected, but transcript is accurate
- User can manually map speaker IDs to names
- System documents limitation clearly

## Next Session TODO

1. [ ] Implement segmented_json parsing (Phase 1)
2. [ ] Remove debug logging
3. [ ] Test with existing multi-speaker videos
4. [ ] Evaluate if threshold needs adjustment
5. [ ] Document findings in README
6. [ ] Commit working implementation
7. [ ] Consider fallback strategies if still detecting single speaker
