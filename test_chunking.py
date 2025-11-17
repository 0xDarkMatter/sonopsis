#!/usr/bin/env python3
"""
Test script for chunking functionality.
Tests token counting and chunking strategy without actual API calls.
"""

from utils.summarizer import ContentSummarizer
from pathlib import Path

# Mock API keys for testing
import os
os.environ['ANTHROPIC_API_KEY'] = 'test_key'
os.environ['OPENAI_API_KEY'] = 'test_key'

# Test different models to show context window variations
test_models = [
    ('claude-sonnet-4-5-20250929', 'Claude Sonnet 4.5'),
    ('gpt-4o', 'GPT-4o'),
    ('openrouter/google/gemini-2.0-flash', 'Gemini 2.0 Flash'),
]

print("=" * 80)
print("MODEL-AWARE CHUNKING TEST")
print("=" * 80)
print()

# Show limits for different models
print("Model Context Windows:")
print("-" * 80)
for model_id, model_name in test_models:
    try:
        summarizer = ContentSummarizer(model=model_id, output_dir='summaries')
        print(f"{model_name:25} | Context: {summarizer.context_window:>10,} tokens | "
              f"Safe Limit: {summarizer.max_input_tokens:>10,} | "
              f"Chunk Size: {summarizer.chunk_target_tokens:>7,}")
    except Exception as e:
        print(f"{model_name:25} | Error: {str(e)}")
print()

# Use Claude Sonnet 4.5 for detailed testing
summarizer = ContentSummarizer(model='claude-sonnet-4-5-20250929', output_dir='summaries')

# Read the 3-hour transcript
transcript_file = Path('transcripts/YT_dnnpyNuPdXs_I_Carried_A_UFO_With_My_Helicopter_-_UFO_Whistleblower_Jake_Barber_transcript.md')

if transcript_file.exists():
    print("=" * 80)
    print("CHUNKING TEST")
    print("=" * 80)
    print()

    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()

    # Test 1: Token counting
    print("Test 1: Token Counting")
    print("-" * 80)
    tokens = summarizer._count_tokens(transcript)
    words = len(transcript.split())
    print(f"Transcript length: {len(transcript):,} characters")
    print(f"Word count: {words:,} words")
    print(f"Token count: {tokens:,} tokens")
    print(f"Ratio: {tokens/words:.2f} tokens per word")
    print()

    # Test 2: Chunking strategy
    print("Test 2: Chunking Strategy")
    print("-" * 80)
    chunks = summarizer._chunk_transcript(transcript, {'title': 'Test Video'})
    print(f"Number of chunks: {len(chunks)}")
    print()

    for idx, (chunk_text, start_line, end_line) in enumerate(chunks, 1):
        chunk_tokens = summarizer._count_tokens(chunk_text)
        chunk_words = len(chunk_text.split())
        print(f"Chunk {idx}:")
        print(f"  Lines: {start_line}-{end_line}")
        print(f"  Tokens: {chunk_tokens:,} (target: ~40,000)")
        print(f"  Words: {chunk_words:,}")
        print(f"  Characters: {len(chunk_text):,}")
        print()

    # Test 3: Threshold check
    print("Test 3: Threshold Check")
    print("-" * 80)
    system_prompt_file = Path('docs/system_prompt.md')
    if system_prompt_file.exists():
        with open(system_prompt_file, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
        system_tokens = summarizer._count_tokens(system_prompt)
    else:
        system_tokens = 3000  # Estimate

    metadata_tokens = 1000  # Estimate
    total_input = tokens + system_tokens + metadata_tokens + 1000

    print(f"Transcript tokens: {tokens:,}")
    print(f"System prompt tokens: {system_tokens:,}")
    print(f"Metadata + overhead: ~{metadata_tokens + 1000:,}")
    print(f"Total input tokens: {total_input:,}")
    print()
    print(f"Max allowed: {summarizer.max_input_tokens:,}")
    print(f"Would trigger chunking: {'YES' if total_input > summarizer.max_input_tokens else 'NO'}")
    print()

    # Test 4: Simulated decision
    print("Test 4: Processing Decision")
    print("-" * 80)
    if total_input > summarizer.max_input_tokens:
        print(f"✓ Chunking REQUIRED")
        print(f"  Exceeded by: {total_input - summarizer.max_input_tokens:,} tokens")
        print(f"  Will use map-reduce strategy with {len(chunks)} chunks")
    else:
        print(f"✓ Single-pass processing OK")
        print(f"  Buffer remaining: {summarizer.max_input_tokens - total_input:,} tokens")
        print(f"  Utilization: {total_input / summarizer.max_input_tokens * 100:.1f}%")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
else:
    print(f"Error: Transcript file not found: {transcript_file}")
