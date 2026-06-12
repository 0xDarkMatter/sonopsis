"""
Speaker-Count Inference
Infers how many people speak in a video from its metadata, via the Claude
Code CLI. Used to auto-hint pyannote diarization (--auto-speakers).

Validated in benchmarks/exp-speaker-inference.md: 5/5 correct at high
confidence with zero harmful predictions across 8 live-metadata cases.
The gate matters: the diarization sweep proved a WRONG count actively
degrades results, so anything below high confidence returns None and the
pipeline diarizes unhinted (today's behavior).
"""

import json
import re
import shutil
import subprocess
from typing import Any, Dict, Optional

# Counts outside this range are treated as inference failures. Also caps the
# blast radius of the untrusted description text feeding the LLM: the only
# thing that can flow back into the pipeline is a small integer.
MAX_REASONABLE_SPEAKERS = 8

PROMPT = """You estimate how many distinct people speak substantially in a YouTube video, using ONLY its metadata.

Respond with STRICT JSON, nothing else:
{"num_speakers": <integer or null>, "confidence": "high"|"medium"|"low", "rationale": "<one short sentence>"}

Rules:
- Count people who speak at length (hosts + guests). Ignore intro clips, ads, samples.
- Music videos, songs, ambience streams, montages: num_speakers = null, confidence = "low".
- Use format knowledge (interview podcast = host + guest) AND names in the title/description.
- BE CONSERVATIVE: answer "high" confidence only when the format and participant list are explicit. A wrong count is worse than no count.

Video metadata:
"""


def infer_speaker_count(video_metadata: Dict[str, Any]) -> Optional[int]:
    """
    Infer the speaker count from video metadata.

    Returns the count only when the LLM reports high confidence and the
    value is plausible; returns None in every other case (no Claude CLI,
    low confidence, parse failure, implausible count) so callers can fall
    back to unhinted diarization.
    """
    cli = shutil.which("claude")
    if not cli:
        return None

    payload = PROMPT + json.dumps({
        "title": video_metadata.get("title", ""),
        "channel": video_metadata.get("uploader", ""),
        "duration_minutes": round((video_metadata.get("duration") or 0) / 60),
        "description": (video_metadata.get("description") or "")[:1500],
    }, indent=2, ensure_ascii=False)

    try:
        result = subprocess.run(
            [cli, "-p", "--output-format", "json", "--model", "haiku",
             "--disallowedTools", "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch,Task"],
            input=payload, capture_output=True, text=True, encoding="utf-8",
            timeout=180,
        )
        if result.returncode != 0:
            return None

        text = json.loads(result.stdout).get("result", "")
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        prediction = json.loads(match.group(0))

        count = prediction.get("num_speakers")
        if str(prediction.get("confidence", "")).lower() != "high":
            return None
        if not isinstance(count, int) or not (1 <= count <= MAX_REASONABLE_SPEAKERS):
            return None

        rationale = str(prediction.get("rationale", ""))[:100]
        print(f"[*] Inferred speaker count: {count} (high confidence: {rationale})")
        return count

    except Exception:
        # Inference is strictly best-effort - any failure means "no hint"
        return None
