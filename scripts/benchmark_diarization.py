"""
Benchmark speaker diarization against known-good RTTM references.

Corpus convention: benchmarks/corpus-diarization/<name>.wav paired with
<name>.rttm (reference speaker turns). Generate with
scripts/make_diarization_corpus.py.

Rubric: DER (diarization error rate = missed speech + false alarm + speaker
confusion, 0.25s collar) via pyannote.metrics, plus detected-vs-true speaker
count. Engines must expose speaker turns: parakeet-dia returns them natively;
elevenlabs turns are parsed from its timestamped transcript (turn end
approximated by the next turn's start).

Usage:
    python scripts/benchmark_diarization.py
    python scripts/benchmark_diarization.py --engines parakeet-dia elevenlabs
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

LINE_RE = re.compile(r"\*\*\[([^\]]+)\]\*\* `\[(\d+):(\d+):(\d+)\]`")


def load_rttm(path: Path):
    """Reference RTTM -> pyannote Annotation."""
    from pyannote.core import Annotation, Segment
    ann = Annotation()
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts and parts[0] == "SPEAKER":
            start, dur, spk = float(parts[3]), float(parts[4]), parts[7]
            ann[Segment(start, start + dur)] = spk
    return ann


def turns_to_annotation(turns):
    """[(start, end, speaker)] -> pyannote Annotation."""
    from pyannote.core import Annotation, Segment
    ann = Annotation()
    for start, end, spk in turns:
        if end > start:
            ann[Segment(start, end)] = spk
    return ann


def parse_transcript_turns(text: str, audio_end: float):
    """Recover turns from the markdown transcript format (start timestamps
    only - each turn ends where the next begins)."""
    starts = []
    for m in LINE_RE.finditer(text):
        spk = m.group(1)
        t = int(m.group(2)) * 3600 + int(m.group(3)) * 60 + int(m.group(4))
        starts.append((t, spk))
    turns = []
    for i, (t, spk) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else audio_end
        turns.append((float(t), float(end), spk))
    return turns


def run_engine(engine: str, audio: Path, out_dir: Path, num_speakers=None,
               min_speakers=None, max_speakers=None, merge_gap=0.8):
    transcriber = AudioTranscriber(output_dir=str(out_dir), engine=engine,
                                   num_speakers=num_speakers,
                                   min_speakers=min_speakers,
                                   max_speakers=max_speakers,
                                   dia_merge_gap=merge_gap)
    start = time.time()
    result = transcriber.transcribe(str(audio))
    elapsed = time.time() - start

    if 'turns' in result:
        turns = result['turns']
    else:
        duration = AudioTranscriber._get_audio_duration(str(audio))
        turns = parse_transcript_turns(result['text'], duration)
    return turns, elapsed


def main():
    parser = argparse.ArgumentParser(description="Benchmark diarization (DER vs reference RTTM)")
    parser.add_argument("--corpus", default=str(Path(__file__).parent.parent / "benchmarks" / "corpus-diarization"))
    parser.add_argument("--engines", nargs="+", default=["parakeet-dia"],
                        help="Engines exposing speaker turns: parakeet-dia, elevenlabs, openai")
    parser.add_argument("--report", default=str(Path(__file__).parent.parent / "benchmarks" / "results-diarization.md"))
    parser.add_argument("--hint-speakers", action="store_true",
                        help="Pass the true speaker count (from the RTTM) to engines that accept it")
    parser.add_argument("--min-speakers", type=int, default=None)
    parser.add_argument("--max-speakers", type=int, default=None)
    parser.add_argument("--merge-gap", type=float, default=0.8,
                        help="Merge adjacent same-speaker turns closer than this (seconds)")
    args = parser.parse_args()

    from pyannote.metrics.diarization import DiarizationErrorRate

    corpus = sorted(Path(args.corpus).glob("*.wav"))
    pairs = [(w, w.with_suffix(".rttm")) for w in corpus if w.with_suffix(".rttm").exists()]
    if not pairs:
        print(f"[!] No (wav, rttm) pairs in {args.corpus} - run scripts/make_diarization_corpus.py")
        sys.exit(1)

    out_dir = Path(args.report).parent / "transcripts"
    rows = []
    for engine in args.engines:
        for audio, rttm in pairs:
            reference = load_rttm(rttm)
            true_speakers = len(reference.labels())
            print(f"\n=== {engine} on {audio.name} ({true_speakers} speakers) ===")
            try:
                hint = true_speakers if args.hint_speakers else None
                turns, elapsed = run_engine(engine, audio, out_dir, num_speakers=hint,
                                            min_speakers=args.min_speakers,
                                            max_speakers=args.max_speakers,
                                            merge_gap=args.merge_gap)
                hypothesis = turns_to_annotation(turns)
                metric = DiarizationErrorRate(collar=0.25)
                der = metric(reference, hypothesis)
                detected = len(hypothesis.labels())
                rows.append({"engine": engine, "file": audio.name, "der": der,
                             "spk": f"{detected}/{true_speakers}", "seconds": elapsed, "error": None})
                print(f"--> DER {der:.1%}, speakers {detected}/{true_speakers}, {elapsed:.1f}s")
            except Exception as e:
                rows.append({"engine": engine, "file": audio.name, "der": None,
                             "spk": "-", "seconds": None, "error": str(e)[:150]})
                print(f"--> FAILED: {e}")

    lines = ["# Speaker Diarization Benchmark", "",
             "DER = diarization error rate vs reference RTTM, 0.25s collar (lower is better).",
             "Speakers = detected/true.", "",
             "| Engine | File | DER | Speakers | Time (s) |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["der"] is None, x["der"] or 0)):
        if r["error"]:
            lines.append(f"| {r['engine']} | {r['file']} | FAILED: {r['error'][:60]} | - | - |")
        else:
            lines.append(f"| {r['engine']} | {r['file']} | {r['der']:.1%} | {r['spk']} | {r['seconds']:.1f} |")
    report = "\n".join(lines) + "\n"
    Path(args.report).write_text(report, encoding="utf-8")
    print(f"\n{report}\nSaved to {args.report}")


if __name__ == "__main__":
    main()
