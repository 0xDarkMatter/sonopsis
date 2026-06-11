# Transcription Engine Benchmark

WER = word error rate vs known-good reference (lower is better).
RTF = transcription seconds per audio second (lower is faster).

| Engine | File | WER | Time (s) | RTF |
|---|---|---|---|---|
| parakeet | ls01_noise_mild.wav | 0.0% | 3.3 | 0.57 |
| parakeet | ls02_noise_heavy.wav | 0.0% | 3.4 | 0.70 |
| parakeet | ls02_noise_mild.wav | 0.0% | 3.6 | 0.75 |
| parakeet | ls02_phone.wav | 0.0% | 3.4 | 0.70 |
| parakeet | ls03_noise_heavy.wav | 0.0% | 3.5 | 0.28 |
| parakeet | ls03_noise_mild.wav | 0.0% | 3.4 | 0.27 |
| parakeet | ls03_phone.wav | 0.0% | 3.5 | 0.28 |
| parakeet | ls04_noise_heavy.wav | 4.2% | 3.4 | 0.34 |
| parakeet | ls04_noise_mild.wav | 4.2% | 3.6 | 0.36 |
| parakeet | ls04_phone.wav | 4.2% | 3.6 | 0.36 |
| parakeet | ls01_noise_heavy.wav | 5.9% | 3.6 | 0.62 |
| parakeet | ls01_phone.wav | 5.9% | 3.3 | 0.57 |
| whisper:base | ls01_noise_heavy.wav | 5.9% | 1.6 | 0.27 |
| whisper:base | ls01_noise_mild.wav | 5.9% | 1.1 | 0.18 |
| whisper:base | ls01_phone.wav | 5.9% | 1.5 | 0.26 |
| whisper:base | ls03_noise_mild.wav | 6.2% | 1.5 | 0.12 |
| whisper:base | ls03_phone.wav | 6.2% | 1.5 | 0.12 |
| whisper:base | ls03_noise_heavy.wav | 9.4% | 2.1 | 0.16 |
| whisper:base | ls04_noise_heavy.wav | 16.7% | 1.5 | 0.16 |
| whisper:base | ls04_noise_mild.wav | 16.7% | 1.5 | 0.16 |
| whisper:base | ls02_noise_heavy.wav | 20.0% | 1.0 | 0.22 |
| whisper:base | ls02_noise_mild.wav | 20.0% | 1.0 | 0.22 |
| whisper:base | ls02_phone.wav | 20.0% | 1.0 | 0.22 |
| whisper:base | ls04_phone.wav | 20.8% | 2.0 | 0.21 |
