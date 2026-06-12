# Speaker Diarization Benchmark

DER = diarization error rate vs reference RTTM, 0.25s collar (lower is better).
Speakers = detected/true.

| Engine | File | DER | Speakers | Time (s) |
|---|---|---|---|---|
| openai | conv_3spk_b.wav | 6.0% | 3/3 | 26.2 |
| openai | conv_4spk_b.wav | 6.4% | 4/4 | 34.8 |
| openai | conv_5spk_b.wav | 7.3% | 5/5 | 36.3 |
| openai | conv_2spk.wav | 9.2% | 2/2 | 13.9 |
| openai | conv_2spk_b.wav | 9.3% | 2/2 | 12.8 |
| openai | conv_4spk.wav | 10.1% | 4/4 | 24.5 |
| openai | conv_3spk.wav | 11.2% | 3/3 | 15.7 |
| openai | conv_3spk_noisy.wav | 12.5% | 3/3 | 16.3 |
| openai | conv_2spk_overlap.wav | 17.7% | 2/2 | 9.7 |
