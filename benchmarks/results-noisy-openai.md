# Transcription Engine Benchmark

WER = word error rate vs known-good reference (lower is better).
RTF = transcription seconds per audio second (lower is faster).

| Engine | File | WER | Time (s) | RTF |
|---|---|---|---|---|
| openai | ls03_noise_heavy.wav | 0.0% | 4.5 | 0.36 |
| openai | ls03_noise_mild.wav | 0.0% | 4.9 | 0.39 |
| openai | ls03_phone.wav | 0.0% | 4.2 | 0.34 |
| openai | ls04_noise_mild.wav | 0.0% | 3.7 | 0.37 |
| openai | ls04_phone.wav | 0.0% | 4.0 | 0.41 |
| openai | ls04_noise_heavy.wav | 4.2% | 3.7 | 0.37 |
| openai | ls01_noise_heavy.wav | 5.9% | 3.8 | 0.64 |
| openai | ls01_noise_mild.wav | 5.9% | 3.2 | 0.55 |
| openai | ls01_phone.wav | 5.9% | 2.9 | 0.49 |
| openai | ls02_noise_mild.wav | 10.0% | 2.5 | 0.52 |
| openai | ls02_phone.wav | 10.0% | 2.2 | 0.47 |
| openai | ls02_noise_heavy.wav | 20.0% | 2.6 | 0.54 |
