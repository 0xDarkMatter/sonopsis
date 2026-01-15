## SPEAKER IDENTIFICATION PROTOCOL

**Context**: This protocol applies to **summaries** only. Transcripts retain raw SPEAKER_X labels from automatic diarization for verification purposes.

When attributing quotes or perspectives throughout **summaries**:

### 1. Analyze Transcript for Speaker Identities

The transcript may contain labels like **[SPEAKER_0]**, **[SPEAKER_1]**, etc. from automatic speaker diarization. Your task is to map these to actual identities.

**Identification Sources** (in priority order):
1. **Self-introductions**: Look for "My name is...", "I'm...", "This is..." in the transcript
2. **Video title**: Often includes speaker names (e.g., "Interview with John Doe")
3. **Channel name**: May indicate host/creator
4. **Context clues**: References to credentials, roles, or names mentioned by other speakers
5. **Speaking patterns**: Interviewer vs. subject, host vs. guest dynamics

**Mapping Process:**
- Read the first 5-10 speaker segments carefully
- Note patterns: Who asks questions (host/interviewer)? Who provides long answers (subject)?
- Look for explicit name mentions: "Jeremy asks...", "Dylan responds..."
- Create a mental map: SPEAKER_0 → [Dylan Borland], SPEAKER_1 → [George Knapp], etc.

### 2. Use Bracket Notation

Once identified, use brackets consistently:
- **Known speakers**: [Jeremy Corbell], [Dylan Borland], [George Knapp]
- **Unknown speakers**: [speaker01], [speaker02], [speaker03]

### 3. Handle Multiple Speakers

If more than 3-4 speakers detected:
- Primary speakers (most speaking time) should be identified first
- Brief speakers or audio clips can be labeled [speaker04], [speaker05], etc.
- Over-segmentation (voice changes, emotion) may create extra speakers - group by role/identity

### 4. Maintain Consistency

- Once you assign a name or placeholder to SPEAKER_X, use it throughout
- If SPEAKER_0 = [Dylan Borland], always refer to SPEAKER_0 as [Dylan Borland]

### 5. Examples

**Transcript Input:**
```
**[SPEAKER_0]** My name is Dylan Borland, former Air Force intelligence...
**[SPEAKER_1]** So, Dylan, you've been talking to Jeremy for years...
**[SPEAKER_2]** Yeah, Dylan, thanks for doing this...
```

**Your Mapping:**
- SPEAKER_0 → [Dylan Borland] (self-introduction)
- SPEAKER_1 → [George Knapp] (host, asks questions, refers to "Jeremy")
- SPEAKER_2 → [Jeremy Corbell] (referred to as "Jeremy")

**Summary Output:**
```
[Dylan Borland] explains his background as a former 1N1 geospatial intelligence specialist...

> "This happens when people violate the Constitution..." - [George Knapp]

[Jeremy Corbell] asks about the timeline of their relationship...
```

### Workflow Summary

1. **Transcription** (ElevenLabs): Generates transcript with **[SPEAKER_0]**, **[SPEAKER_1]**, etc. labels
2. **Summarization** (AI): Reads transcript, identifies speakers using this protocol, outputs **[Name]** format
3. **Result**:
   - Transcript file: Raw SPEAKER_X labels (verifiable data)
   - Summary file: Human-readable [Name] format (interpreted data)
