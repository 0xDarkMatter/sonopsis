# Transcription Engine Benchmark

WER = word error rate vs known-good reference (lower is better).
RTF = transcription seconds per audio second (lower is faster).

| Engine | File | WER | Time (s) | RTF |
|---|---|---|---|---|
| parakeet | librispeech_01.wav | 0.0% | 3.3 | 0.57 |
| parakeet | librispeech_02.wav | 0.0% | 3.3 | 0.69 |
| parakeet | librispeech_03.wav | 0.0% | 3.2 | 0.26 |
| parakeet | librispeech_04.wav | 0.0% | 3.1 | 0.31 |
| whisper:tiny | librispeech_03.wav | 3.1% | 1.0 | 0.08 |
| whisper:base | librispeech_03.wav | 3.1% | 1.5 | 0.12 |
| whisper:tiny | librispeech_04.wav | 4.2% | 1.0 | 0.10 |
| whisper:tiny | librispeech_01.wav | 5.9% | 1.0 | 0.18 |
| whisper:base | librispeech_01.wav | 5.9% | 1.0 | 0.18 |
| whisper:base | librispeech_04.wav | 8.3% | 1.5 | 0.15 |
| whisper:tiny | librispeech_02.wav | 10.0% | 0.5 | 0.11 |
| whisper:base | harvard_list01.wav | 11.2% | 2.5 | 0.08 |
| whisper:tiny | harvard_list01.wav | 15.0% | 2.0 | 0.06 |
| whisper:base | librispeech_02.wav | 20.0% | 1.0 | 0.21 |
| parakeet | harvard_list01.wav | 33.8% | 4.7 | 0.14 |
