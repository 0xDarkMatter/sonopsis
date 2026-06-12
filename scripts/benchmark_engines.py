"""
Benchmark transcription engines against a known-good corpus.

Corpus convention: benchmarks/corpus/<name>.(wav|mp3|flac) paired with
<name>.txt containing the verified 100%-correct reference transcript.

Usage:
    python scripts/benchmark_engines.py
    python scripts/benchmark_engines.py --engines whisper:tiny whisper:base parakeet
    python scripts/benchmark_engines.py --corpus path/to/corpus --report out.md

Rubric: word error rate (WER = Levenshtein distance on normalized words /
reference length) plus wall-clock time and real-time factor. Engines run
sequentially so timings aren't skewed by CPU contention.
"""

import argparse
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from sonopsis.transcriber import AudioTranscriber

load_dotenv(override=True)

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}


def normalize(text: str) -> list:
    """Lowercase, strip diarization markup and punctuation -> word list."""
    # Speaker/timestamp markup from diarizing engines is presentation, not
    # transcription - it must not count as word errors
    text = re.sub(r"\*\*\[[^\]]*\]\*\*", " ", text)
    text = re.sub(r"`\[[^\]]*\]`", " ", text)
    text = text.lower().replace("'", "")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate via Levenshtein distance on normalized word lists."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    # Standard DP edit distance
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        curr = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (r != h))
        prev = curr
    return prev[-1] / len(ref)


def load_corpus(corpus_dir: Path) -> list:
    """Pairs of (audio_path, reference_text)."""
    pairs = []
    for audio in sorted(corpus_dir.iterdir()):
        if audio.suffix.lower() in AUDIO_EXTS:
            ref = audio.with_suffix(".txt")
            if ref.exists():
                pairs.append((audio, ref.read_text(encoding="utf-8").strip()))
            else:
                print(f"[!] Skipping {audio.name}: no matching .txt reference")
    return pairs


def run_engine(spec: str, audio: Path, out_dir: Path) -> dict:
    """spec is 'engine', 'whisper:<size>', or 'parakeet:<int8|fp32>'."""
    engine, _, opt = spec.partition(":")
    kwargs = {}
    if engine.startswith("parakeet") and opt:
        kwargs["parakeet_quant"] = None if opt == "fp32" else opt
        opt = ""
    transcriber = AudioTranscriber(
        model_name=opt or "base",
        output_dir=str(out_dir),
        engine=engine,
        **kwargs,
    )
    start = time.time()
    result = transcriber.transcribe(str(audio))
    elapsed = time.time() - start
    return {"text": result["text"], "seconds": elapsed}


def main():
    parser = argparse.ArgumentParser(description="Benchmark transcription engines (WER vs known-good transcripts)")
    parser.add_argument("--corpus", default=str(Path(__file__).parent.parent / "benchmarks" / "corpus"))
    parser.add_argument("--engines", nargs="+",
                        default=["whisper:tiny", "whisper:base", "parakeet"],
                        help="Engine specs: whisper:<size>, whisperx:<size>, parakeet, elevenlabs, openai")
    parser.add_argument("--report", default=str(Path(__file__).parent.parent / "benchmarks" / "results.md"))
    args = parser.parse_args()

    corpus = load_corpus(Path(args.corpus))
    if not corpus:
        print(f"[!] No (audio, .txt) pairs found in {args.corpus}")
        sys.exit(1)

    out_dir = Path(args.report).parent / "transcripts"
    rows = []
    for spec in args.engines:
        for audio, reference in corpus:
            duration = AudioTranscriber._get_audio_duration(str(audio)) or 0
            print(f"\n=== {spec} on {audio.name} ===")
            try:
                r = run_engine(spec, audio, out_dir)
                error_rate = wer(reference, r["text"])
                rows.append({
                    "engine": spec, "file": audio.name, "wer": error_rate,
                    "seconds": r["seconds"],
                    "rtf": (r["seconds"] / duration) if duration else None,
                    "error": None,
                })
                print(f"--> WER {error_rate:.1%} in {r['seconds']:.1f}s")
            except Exception as e:
                rows.append({"engine": spec, "file": audio.name, "wer": None,
                             "seconds": None, "rtf": None, "error": str(e)[:120]})
                print(f"--> FAILED: {e}")

    # Report
    lines = ["# Transcription Engine Benchmark", "",
             "WER = word error rate vs known-good reference (lower is better).",
             "RTF = transcription seconds per audio second (lower is faster).", "",
             "| Engine | File | WER | Time (s) | RTF |",
             "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["wer"] is None, x["wer"] or 0)):
        if r["error"]:
            lines.append(f"| {r['engine']} | {r['file']} | FAILED | - | - | ")
        else:
            rtf = f"{r['rtf']:.2f}" if r["rtf"] else "-"
            lines.append(f"| {r['engine']} | {r['file']} | {r['wer']:.1%} | {r['seconds']:.1f} | {rtf} |")
    report = "\n".join(lines) + "\n"
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(report, encoding="utf-8")
    print(f"\n{report}\nSaved to {args.report}")


if __name__ == "__main__":
    main()
