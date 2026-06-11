# Transcription Engine Benchmark

WER = word error rate vs known-good reference (lower is better).
RTF = transcription seconds per audio second (lower is faster).

| Engine | File | WER | Time (s) | RTF |
|---|---|---|---|---|
| parakeet:fp32 | ls02_noise_mild.wav | 0.0% | 4.0 | 0.84 |
| parakeet:fp32 | ls02_phone.wav | 0.0% | 3.9 | 0.81 |
| parakeet:fp32 | ls03_noise_heavy.wav | 0.0% | 4.2 | 0.34 |
| parakeet:fp32 | ls03_noise_mild.wav | 0.0% | 4.2 | 0.34 |
| parakeet:fp32 | ls03_phone.wav | 0.0% | 4.2 | 0.34 |
| parakeet:fp32 | ls04_noise_mild.wav | 0.0% | 4.3 | 0.44 |
| parakeet:fp32 | ls04_phone.wav | 0.0% | 4.1 | 0.42 |
| parakeet:fp32 | ls04_noise_heavy.wav | 4.2% | 4.4 | 0.44 |
| parakeet:fp32 | ls01_noise_heavy.wav | 5.9% | 44.0 | 7.51 |
| parakeet:fp32 | ls01_noise_mild.wav | 5.9% | 3.9 | 0.67 |
| parakeet:fp32 | ls01_phone.wav | 5.9% | 4.0 | 0.68 |
| parakeet:fp32 | ls02_noise_heavy.wav | 10.0% | 3.9 | 0.82 |
