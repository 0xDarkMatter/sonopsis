# Acoustic Speaker-Count Probe Experiment

Sweep k=2..5, score cosine silhouette of turn embeddings, pick best k.

| File | True | Unhinted pyannote | Probe pick | Silhouettes (k2..k5) |
|---|---|---|---|---|
| conv_2spk | 2 | 2 | **2** | 0.792, 0.484, -0.021, -0.059 |
| conv_2spk_overlap | 2 | 2 | **2** | 0.690, 0.483, -0.197, -0.181 |
| conv_3spk | 3 | 2 | **2** | 0.497, 0.446, 0.158, -0.156 |
| conv_3spk_noisy | 3 | 2 | **3** | 0.318, 0.369, 0.163, 0.067 |
| conv_4spk | 4 | 3 | **3** | 0.358, 0.524, 0.521, 0.388 |

- Unhinted correct: 2/5
- Probe correct: 3/5
- Probe cost: ~4 extra diarization passes per video
