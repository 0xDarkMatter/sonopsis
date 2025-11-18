#!/usr/bin/env python3
"""
Direct test of Gemini CLI summarization on existing transcript
"""
import sys
sys.path.insert(0, '/Users/mack/projects/sonopsis')

from utils.summarizer import ContentSummarizer
from pathlib import Path

# Path to existing transcript
transcript_path = Path("transcripts/YT_kO41iURud9c_Brian_Cox_-_The_quantum_roots_of_reality_Full_Interview_transcript.md")

print(f"Testing Gemini CLI summarization on: {transcript_path.name}")
print(f"File size: {transcript_path.stat().st_size / 1024:.1f} KB")
print()

# Read the transcript
with open(transcript_path, 'r', encoding='utf-8') as f:
    transcript_content = f.read()

print(f"Transcript length: {len(transcript_content):,} characters")
print()

# Create summarizer instance
summarizer = ContentSummarizer(
    model='gemini-2.5-pro',
    output_dir='summaries'
)

# Minimal metadata
metadata = {
    'title': 'Brian Cox - The quantum roots of reality | Full Interview',
    'uploader': 'YouTube',
    'duration': '01:19:41',
    'url': 'https://www.youtube.com/watch?v=kO41iURud9c',
    'language': 'eng'
}

# Run summarization
print("Starting Gemini CLI summarization...")
print("=" * 60)
summary_data = summarizer.summarize(
    transcript_content,
    metadata,
    analysis_mode='advanced',
    transcription_engine='elevenlabs'
)
summary = summary_data['summary']
print("=" * 60)
print()

# Save summary
output_path = Path("summaries/YT_kO41iURud9c_Brian_Cox_-_The_quantum_roots_of_reality_Full_Interview_summary.md")
output_path.parent.mkdir(exist_ok=True)

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(summary)

print(f"✓ Summary saved to: {output_path}")
print(f"✓ Summary length: {len(summary):,} characters")
print()
print("First 500 characters of summary:")
print("-" * 60)
print(summary[:500])
print("-" * 60)
