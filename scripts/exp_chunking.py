"""
Experiment: hard-cut vs silence-aligned chunk boundaries for long audio.

Builds a ~105s sample by looping the LibriSpeech corpus files (reference text
known exactly), then transcribes with Parakeet using deliberately tiny 10s
chunks so boundary effects dominate. Compares WER with alignment off vs on.

Usage: python scripts/exp_chunking.py
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from sonopsis.transcriber import AudioTranscriber
from scripts.benchmark_engines import wer

ROOT = Path(__file__).parent.parent
CORPUS = ROOT / "benchmarks" / "corpus"
OUT = ROOT / "benchmarks"
REPEATS = 3
CHUNK_SECONDS = 10  # tiny on purpose: one boundary every ~10s stresses cutting


def build_long_sample(work: Path):
    clips = sorted(CORPUS.glob("librispeech_0*.wav"))
    texts = [c.with_suffix(".txt").read_text(encoding="utf-8").strip() for c in clips]
    reference = " ".join(texts * REPEATS)

    concat_list = work / "list.txt"
    lines = []
    for _ in range(REPEATS):
        for c in clips:
            lines.append(f"file '{c.resolve().as_posix()}'")
    concat_list.write_text("\n".join(lines), encoding="utf-8")

    long_wav = work / "long_sample.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(concat_list), "-ac", "1", "-ar", "16000", str(long_wav)],
                   check=True, timeout=300)
    return long_wav, reference


def run(align: bool, long_wav: Path, work: Path):
    t = AudioTranscriber(
        output_dir=str(work / ("aligned" if align else "hardcut")),
        engine="parakeet",
        parakeet_chunk_seconds=CHUNK_SECONDS,
        parakeet_align_silence=align,
    )
    start = time.time()
    result = t.transcribe(str(long_wav))
    return result["text"], time.time() - start


def main():
    work = OUT / "exp-chunking-work"
    work.mkdir(parents=True, exist_ok=True)
    long_wav, reference = build_long_sample(work)
    duration = AudioTranscriber._get_audio_duration(str(long_wav))
    print(f"[*] Long sample: {duration:.1f}s, ~{int(duration // CHUNK_SECONDS)} chunk boundaries\n")

    rows = []
    for align in (False, True):
        label = "silence-aligned" if align else "hard-cut"
        print(f"=== {label} ===")
        text, elapsed = run(align, long_wav, work)
        error = wer(reference, text)
        rows.append((label, error, elapsed))
        print(f"--> WER {error:.2%} in {elapsed:.1f}s\n")

    report = ["# Chunk-Boundary Experiment", "",
              f"~{duration:.0f}s LibriSpeech loop, {CHUNK_SECONDS}s chunks "
              f"(~{int(duration // CHUNK_SECONDS)} boundaries), Parakeet int8.", "",
              "| Strategy | WER | Time (s) |", "|---|---|---|"]
    for label, error, elapsed in rows:
        report.append(f"| {label} | {error:.2%} | {elapsed:.1f} |")
    (OUT / "exp-chunking.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
