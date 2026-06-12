# Transcription Engine Benchmark

WER = word error rate vs known-good reference (lower is better).
RTF = transcription seconds per audio second (lower is faster).

| Engine | File | WER | Time (s) | RTF |
|---|---|---|---|---|
| openai | librispeech_03.wav | 0.0% | 5.0 | 0.40 |
| openai | librispeech_04.wav | 0.0% | 4.2 | 0.42 |
| openai | harvard_list01.wav | 5.0% | 11.8 | 0.35 |
| openai | librispeech_01.wav | 5.9% | 3.1 | 0.53 |
| openai | librispeech_02.wav | 10.0% | 3.3 | 0.68 |
