# Transcription Engine Benchmark

WER = word error rate vs known-good reference (lower is better).
RTF = transcription seconds per audio second (lower is faster).

| Engine | File | WER | Time (s) | RTF |
|---|---|---|---|---|
| parakeet | librispeech_01_8k.wav | 0.0% | 3.6 | 0.61 |
| parakeet | librispeech_02_8k.wav | 0.0% | 2.9 | 0.60 |
| parakeet | librispeech_03_8k.wav | 0.0% | 3.3 | 0.26 |
| parakeet | librispeech_04_8k.wav | 0.0% | 3.2 | 0.33 |
| whisper:base | librispeech_03_8k.wav | 3.1% | 1.5 | 0.12 |
| whisper:base | librispeech_01_8k.wav | 5.9% | 1.7 | 0.28 |
| whisper:base | librispeech_04_8k.wav | 16.7% | 1.5 | 0.16 |
| whisper:base | librispeech_02_8k.wav | 20.0% | 1.0 | 0.22 |
