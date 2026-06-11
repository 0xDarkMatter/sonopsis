"""
Experiment: acoustic speaker-count probe via cluster-quality sweep.

Hypothesis: pyannote miscounts speakers when left alone, but if we run it at
each candidate count k=2..5 and score how acoustically separated the
resulting speaker clusters are (cosine silhouette over turn embeddings), the
best-scoring k is the true count - giving a metadata-free probe whose answer
can be passed back as the num_speakers hint.

Evaluated against the exact-truth diarization corpus.

Usage: python scripts/exp_speaker_probe.py
"""

import sys
import time
import wave as wave_mod
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(override=True)

import os
import torch
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding

CORPUS = ROOT / "benchmarks" / "corpus-diarization"
TRUTH = {"conv_2spk": 2, "conv_2spk_overlap": 2, "conv_3spk": 3,
         "conv_3spk_noisy": 3, "conv_4spk": 4}
K_RANGE = range(2, 6)
MIN_TURN = 0.6  # embeddings on sub-0.6s snippets are unstable


def load_waveform(path: Path):
    with wave_mod.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    return torch.from_numpy(pcm.astype("float32") / 32768.0).unsqueeze(0), sr


def cosine_silhouette(X: np.ndarray, labels: list) -> float:
    """Mean silhouette coefficient with cosine distance (numpy only)."""
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    D = 1.0 - X @ X.T
    labels = np.asarray(labels)
    scores = []
    for i in range(len(labels)):
        same = (labels == labels[i])
        same[i] = False
        if not same.any():
            continue  # singleton cluster - silhouette undefined for this point
        a = D[i][same].mean()
        b = min(D[i][labels == other].mean()
                for other in set(labels) if other != labels[i])
        scores.append((b - a) / max(a, b))
    return float(np.mean(scores)) if scores else -1.0


def diarize_turns(pipeline, waveform, sr, num_speakers=None):
    kwargs = {"num_speakers": num_speakers} if num_speakers else {}
    output = pipeline({"waveform": waveform, "sample_rate": sr}, **kwargs)
    ann = getattr(output, "speaker_diarization", output)
    return [(seg.start, seg.end, spk)
            for seg, _, spk in ann.itertracks(yield_label=True)]


def turn_embeddings(embedder, waveform, sr, turns):
    vecs, labels = [], []
    for start, end, spk in turns:
        if end - start < MIN_TURN:
            continue
        chunk = waveform[:, int(start * sr):int(end * sr)]
        emb = embedder(chunk[None])  # (1, channels, samples) -> (1, dim)
        vecs.append(np.asarray(emb).reshape(-1))
        labels.append(spk)
    return np.vstack(vecs), labels


def main():
    token = os.getenv("HF_TOKEN")
    print("[*] Loading pyannote pipeline + embedding model...")
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-community-1", token=token)
    embedder = PretrainedSpeakerEmbedding(
        "pyannote/wespeaker-voxceleb-resnet34-LM", device=torch.device("cpu"),
        token=token)

    rows = []
    for wav in sorted(CORPUS.glob("conv_*.wav")):
        true_k = TRUTH.get(wav.stem)
        if true_k is None:
            continue
        waveform, sr = load_waveform(wav)
        start_t = time.time()

        # Baseline: what unhinted pyannote believes
        unhinted = len({t[2] for t in diarize_turns(pipeline, waveform, sr)})

        # Sweep k and score cluster separation
        sweep = {}
        for k in K_RANGE:
            turns = diarize_turns(pipeline, waveform, sr, num_speakers=k)
            X, labels = turn_embeddings(embedder, waveform, sr, turns)
            distinct = len(set(labels))
            sil = cosine_silhouette(X, labels) if distinct > 1 else -1.0
            sweep[k] = sil
        probe_k = max(sweep, key=sweep.get)
        elapsed = time.time() - start_t

        rows.append({"file": wav.stem, "true": true_k, "unhinted": unhinted,
                     "probe": probe_k, "sweep": sweep, "seconds": elapsed})
        sweep_str = " ".join(f"k{k}={v:.3f}" for k, v in sweep.items())
        print(f"[{wav.stem}] true={true_k} unhinted={unhinted} probe={probe_k} "
              f"({sweep_str}) {elapsed:.0f}s")

    probe_right = sum(r["probe"] == r["true"] for r in rows)
    unhinted_right = sum(r["unhinted"] == r["true"] for r in rows)

    lines = ["# Acoustic Speaker-Count Probe Experiment", "",
             "Sweep k=2..5, score cosine silhouette of turn embeddings, pick best k.", "",
             "| File | True | Unhinted pyannote | Probe pick | Silhouettes (k2..k5) |",
             "|---|---|---|---|---|"]
    for r in rows:
        sw = ", ".join(f"{v:.3f}" for v in r["sweep"].values())
        lines.append(f"| {r['file']} | {r['true']} | {r['unhinted']} | "
                     f"**{r['probe']}** | {sw} |")
    lines += ["", f"- Unhinted correct: {unhinted_right}/{len(rows)}",
              f"- Probe correct: {probe_right}/{len(rows)}",
              f"- Probe cost: ~4 extra diarization passes per video"]
    report = "\n".join(lines) + "\n"
    (ROOT / "benchmarks" / "exp-speaker-probe.md").write_text(report, encoding="utf-8")
    print(f"\n{report}")


if __name__ == "__main__":
    main()
