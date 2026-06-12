# Acoustic Speaker-Count Probe Experiment

Sweep k=2..6, cosine silhouette of turn embeddings.
argmax = naive best; eps = largest k within 0.06 of best (hypothesis).

| File | True | Unhinted | argmax | eps-rule | Silhouettes |
|---|---|---|---|---|---|
| conv_2spk_b | 2 | 2 | 2 | **2** | 0.825, 0.570, -0.027, -0.093, -0.102 |
| conv_3spk_b | 3 | 3 | 3 | **3** | 0.561, 0.585, 0.443, 0.287, 0.306 |
| conv_4spk_b | 4 | 4 | 4 | **4** | 0.409, 0.647, 0.811, 0.538, 0.162 |
| conv_5spk_b | 5 | 5 | 6 | **6** | 0.327, 0.498, 0.432, 0.577, 0.619 |

- Unhinted correct: 4/4
- argmax correct: 3/4
- eps-rule correct: 3/4
- Probe cost: ~5 extra diarization passes per video
