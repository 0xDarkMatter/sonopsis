"""
Experiment: infer speaker count from YouTube metadata with an LLM.

The diarization sweep proved exact num_speakers is the strongest accuracy
lever - and that a WRONG hint actively hurts. So the question is not just
"can the LLM guess the count" but "does it only commit when it's right".

Test cases are real videos fetched live via yt-dlp (metadata only, no
download); expected counts come from well-known formats. The LLM sees only
what the pipeline would see: title, channel, duration, description.

Scoring: accuracy on high-confidence predictions (the only ones a gated
integration would use), coverage, and harm rate (high-confidence + wrong).

Usage: python scripts/exp_speaker_inference.py
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yt_dlp
from dotenv import load_dotenv

# Video titles routinely contain emoji - keep Windows consoles alive
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(override=True)

ROOT = Path(__file__).parent.parent

# (lookup, expected_count or None for "should abstain", format note)
CASES = [
    ("https://www.youtube.com/watch?v=jNQXAC9IVRw", 1, "Me at the zoo - single speaker"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", None, "music video - should abstain"),
    ("ytsearch1:lex fridman podcast interview episode", 2, "interview podcast host+guest"),
    ("ytsearch1:TED talk official", 1, "single TED speaker"),
    ("ytsearch1:kurzgesagt in a nutshell video", 1, "single narrator"),
    ("ytsearch1:joe rogan experience full episode guest", 2, "interview host+guest"),
    ("ytsearch1:all-in podcast full episode besties", 4, "4-host panel"),
    ("ytsearch1:lofi hip hop radio beats to relax", None, "music stream - should abstain"),
]

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


def fetch_metadata(lookup: str) -> dict:
    opts = {"quiet": True, "no_warnings": True, "extract_flat": False, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(lookup, download=False)
        if "entries" in info:  # search result
            info = info["entries"][0]
    return {
        "title": info.get("title", ""),
        "channel": info.get("uploader", ""),
        "duration_minutes": round((info.get("duration") or 0) / 60),
        "description": (info.get("description") or "")[:1500],
    }


def ask_llm(metadata: dict) -> dict:
    cli = shutil.which("claude")
    if not cli:
        print("[!] Claude Code CLI required for this experiment")
        sys.exit(1)
    payload = PROMPT + json.dumps(metadata, indent=2, ensure_ascii=False)
    result = subprocess.run(
        [cli, "-p", "--output-format", "json", "--model", "haiku",
         "--disallowedTools", "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch,Task"],
        input=payload, capture_output=True, text=True, encoding="utf-8", timeout=300,
    )
    response = json.loads(result.stdout)
    text = response.get("result", "")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0)) if match else {"num_speakers": None, "confidence": "low",
                                                     "rationale": "unparseable"}


def main():
    rows = []
    for lookup, expected, note in CASES:
        print(f"\n=== {note} ===")
        try:
            meta = fetch_metadata(lookup)
            print(f"    {meta['title'][:70]} ({meta['channel']})")
            pred = ask_llm(meta)
            rows.append({"note": note, "video": meta["title"][:50], "expected": expected,
                         "predicted": pred.get("num_speakers"),
                         "confidence": pred.get("confidence", "low"),
                         "rationale": pred.get("rationale", "")[:80], "error": None})
            print(f"--> predicted {pred.get('num_speakers')} ({pred.get('confidence')}): "
                  f"{pred.get('rationale', '')[:80]}")
        except Exception as e:
            rows.append({"note": note, "video": "?", "expected": expected, "predicted": "ERR",
                         "confidence": "-", "rationale": str(e)[:80], "error": str(e)})
            print(f"--> FAILED: {e}")

    # Gated scoring: only high-confidence predictions would be used
    high = [r for r in rows if not r["error"] and r["confidence"] == "high"]
    high_correct = [r for r in high if r["predicted"] == r["expected"]]
    abstain_ok = [r for r in rows if not r["error"] and r["expected"] is None
                  and (r["predicted"] is None or r["confidence"] != "high")]

    lines = ["# LLM Speaker-Count Inference Experiment", "",
             "Gate: only high-confidence predictions would feed pyannote's num_speakers.", "",
             "| Case | Video | Expected | Predicted | Confidence |",
             "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['note']} | {r['video']} | {r['expected']} | "
                     f"{r['predicted']} | {r['confidence']} |")
    lines += ["",
              f"- High-confidence predictions: {len(high)}/{len(rows)} (coverage)",
              f"- Correct when high-confidence: {len(high_correct)}/{len(high)}"
              + (" (accuracy@high)" if high else ""),
              f"- HARMFUL (high-confidence but wrong): {len(high) - len(high_correct)}",
              f"- Abstained appropriately on non-speech: {len(abstain_ok)}/"
              f"{len([r for r in rows if r['expected'] is None])}"]
    report = "\n".join(lines) + "\n"
    (ROOT / "benchmarks" / "exp-speaker-inference.md").write_text(report, encoding="utf-8")
    print(f"\n{report}")


if __name__ == "__main__":
    main()
