"""
Build a known-good speaker-diarization corpus.

Constructs synthetic conversations by interleaving LibriSpeech utterances
from different speakers with silence gaps. Because we control the assembly,
the reference RTTM (who speaks when) is exact by construction - no human
annotation needed.

Usage:
    python scripts/make_diarization_corpus.py
Outputs:
    benchmarks/corpus-diarization/conv_2spk.wav + .rttm
    benchmarks/corpus-diarization/conv_3spk.wav + .rttm  (if speakers allow)
"""

import json
import subprocess
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "benchmarks" / "corpus-diarization"


def rows_urls(split: str) -> list:
    """Multiple offsets so the sample set spans several distinct speakers."""
    return [
        ("https://datasets-server.huggingface.co/rows?dataset="
         f"openslr%2Flibrispeech_asr&config=clean&split={split}&offset={off}&length=20")
        for off in (0, 600, 1200, 1800, 2400)
    ]
GAP_SECONDS = 0.7
UTTERANCES_PER_SPEAKER = 3


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True, timeout=30)
    return float(json.loads(out.stdout)["format"]["duration"])


def build_conversation(name: str, speaker_clips: dict):
    """Interleave clips round-robin across speakers; emit wav + exact RTTM."""
    work = OUT_DIR / "_work"
    work.mkdir(parents=True, exist_ok=True)

    # Round-robin order: spk1-utt1, spk2-utt1, ..., spk1-utt2, ...
    order = []
    for i in range(UTTERANCES_PER_SPEAKER):
        for spk, clips in speaker_clips.items():
            if i < len(clips):
                order.append((spk, clips[i]))

    # Normalize every clip to 16kHz mono and measure durations
    segments, t = [], 0.0
    parts = []
    for idx, (spk, clip) in enumerate(order):
        norm = work / f"{name}_{idx:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
                        "-ac", "1", "-ar", "16000", str(norm)], check=True, timeout=60)
        dur = ffprobe_duration(norm)
        segments.append((t, dur, spk))
        parts.append(norm)
        t += dur + GAP_SECONDS

    # Concatenate with silence gaps via ffmpeg filter
    inputs, filters = [], []
    for i, p in enumerate(parts):
        inputs += ["-i", str(p)]
        filters.append(f"[{i}:a]")
    # Build: clip0 [sil] clip1 [sil] ... using concat - simplest is per-pair files;
    # use apad on each clip instead (pad after each clip with the gap)
    pad_filters = "".join(
        f"[{i}:a]apad=pad_dur={GAP_SECONDS}[p{i}];" for i in range(len(parts)))
    concat_in = "".join(f"[p{i}]" for i in range(len(parts)))
    filter_complex = f"{pad_filters}{concat_in}concat=n={len(parts)}:v=0:a=1[out]"

    out_wav = OUT_DIR / f"{name}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", filter_complex, "-map", "[out]", str(out_wav)],
                   check=True, timeout=300)

    # Reference RTTM (exact by construction)
    rttm = OUT_DIR / f"{name}.rttm"
    with open(rttm, "w", encoding="utf-8") as f:
        for start, dur, spk in segments:
            f.write(f"SPEAKER {name} 1 {start:.3f} {dur:.3f} <NA> <NA> {spk} <NA> <NA>\n")

    for p in parts:
        p.unlink()
    print(f"[+] {out_wav.name}: {len(segments)} turns, "
          f"{len(speaker_clips)} speakers, {t:.1f}s")


def build_overlap_conversation(name: str, speaker_clips: dict, overlap: float = 1.0):
    """Like build_conversation, but each turn starts before the previous one
    ends - crosstalk with an exact overlapping reference RTTM."""
    work = OUT_DIR / "_work"
    work.mkdir(parents=True, exist_ok=True)

    order = []
    for i in range(UTTERANCES_PER_SPEAKER):
        for spk, clips in speaker_clips.items():
            if i < len(clips):
                order.append((spk, clips[i]))

    segments, t = [], 0.0
    inputs, delays = [], []
    for idx, (spk, clip) in enumerate(order):
        norm = work / f"{name}_{idx:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
                        "-ac", "1", "-ar", "16000", str(norm)], check=True, timeout=60)
        dur = ffprobe_duration(norm)
        segments.append((t, dur, spk))
        inputs += ["-i", str(norm)]
        delays.append(int(t * 1000))
        t += dur - overlap  # next speaker starts before this one finishes

    delay_filters = "".join(
        f"[{i}:a]adelay={d}|{d}[d{i}];" for i, d in enumerate(delays))
    mix_in = "".join(f"[d{i}]" for i in range(len(delays)))
    filter_complex = f"{delay_filters}{mix_in}amix=inputs={len(delays)}:normalize=0[out]"

    out_wav = OUT_DIR / f"{name}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", filter_complex, "-map", "[out]", str(out_wav)],
                   check=True, timeout=300)

    with open(OUT_DIR / f"{name}.rttm", "w", encoding="utf-8") as f:
        for start, dur, spk in segments:
            f.write(f"SPEAKER {name} 1 {start:.3f} {dur:.3f} <NA> <NA> {spk} <NA> <NA>\n")

    for i in range(len(order)):
        (work / f"{name}_{i:02d}.wav").unlink(missing_ok=True)
    print(f"[+] {out_wav.name}: {len(segments)} turns with {overlap}s crosstalk overlap")


def fetch_speakers(split: str):
    """Group sample audio URLs by speaker for a LibriSpeech split."""
    rows = []
    for url in rows_urls(split):
        with urllib.request.urlopen(url, timeout=60) as r:
            rows.extend(json.loads(r.read())["rows"])

    by_speaker = defaultdict(list)
    for row in rows:
        r = row["row"]
        audio = r["audio"][0]["src"] if isinstance(r["audio"], list) else r["audio"]["src"]
        by_speaker[str(r["speaker_id"])].append(audio)

    speakers = [s for s, clips in by_speaker.items() if len(clips) >= UTTERANCES_PER_SPEAKER]
    print(f"[*] {split} split: speakers with >= {UTTERANCES_PER_SPEAKER} utterances: {speakers}")
    return by_speaker, speakers


def download(by_speaker, spk_list, tag):
    work = OUT_DIR / "_work"
    work.mkdir(parents=True, exist_ok=True)
    clips = {}
    for spk in spk_list:
        paths = []
        for j, url in enumerate(by_speaker[spk][:UTTERANCES_PER_SPEAKER]):
            p = work / f"raw_{tag}_{spk}_{j}.wav"
            urllib.request.urlretrieve(url, p)
            paths.append(p)
        clips[f"spk_{spk}"] = paths
    return clips


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[*] Fetching LibriSpeech sample metadata...")
    by_speaker, speakers = fetch_speakers("validation")
    if len(speakers) < 2:
        print("[!] Need at least 2 distinct speakers in the sample set")
        sys.exit(1)

    work = OUT_DIR / "_work"
    work.mkdir(parents=True, exist_ok=True)

    clips2 = download(by_speaker, speakers[:2], "2spk")
    build_conversation("conv_2spk", clips2)
    build_overlap_conversation("conv_2spk_overlap", clips2)

    if len(speakers) >= 3:
        clips3 = download(by_speaker, speakers[:3], "3spk")
        build_conversation("conv_3spk", clips3)

    if len(speakers) >= 4:
        clips4 = download(by_speaker, speakers[:4], "4spk")
        build_conversation("conv_4spk", clips4)

    # Held-out set from the TEST split: entirely different speakers, so
    # selection rules tuned on the primary set can be validated without
    # overfitting. Includes a 5-speaker case the primary set lacks.
    by_speaker_t, speakers_t = fetch_speakers("test")
    for n in (2, 3, 4, 5):
        if len(speakers_t) >= n:
            clips = download(by_speaker_t, speakers_t[:n], f"{n}spk_b")
            build_conversation(f"conv_{n}spk_b", clips)

    # Noisy variant of the 3-speaker conversation: pink noise changes the
    # audio but not who-speaks-when, so the reference RTTM stays exact
    src = OUT_DIR / "conv_3spk.wav"
    if src.exists():
        noisy = OUT_DIR / "conv_3spk_noisy.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
             "-filter_complex",
             "anoisesrc=colour=pink:amplitude=0.06:duration=120[n];[0:a][n]amix=inputs=2:duration=first",
             str(noisy)], check=True, timeout=120)
        ref = (OUT_DIR / "conv_3spk.rttm").read_text(encoding="utf-8")
        (OUT_DIR / "conv_3spk_noisy.rttm").write_text(
            ref.replace("conv_3spk", "conv_3spk_noisy"), encoding="utf-8")
        print("[+] conv_3spk_noisy.wav: pink-noise variant with identical turns")

    # Clean raw downloads
    for p in work.glob("raw_*"):
        p.unlink()
    try:
        work.rmdir()
    except OSError:
        pass


if __name__ == "__main__":
    main()
