#!/usr/bin/env python3
"""
Test Gemini CLI integration with a real transcript.
"""

import os
from pathlib import Path
from utils.summarizer import ContentSummarizer

# Read the transcript
transcript_file = Path('transcripts/YT_dnnpyNuPdXs_I_Carried_A_UFO_With_My_Helicopter_-_UFO_Whistleblower_Jake_Barber_transcript.md')

print("=" * 80)
print("GEMINI CLI TEST")
print("=" * 80)
print()

if not transcript_file.exists():
    print(f"Error: Transcript file not found: {transcript_file}")
    exit(1)

# Read transcript
with open(transcript_file, 'r', encoding='utf-8') as f:
    transcript_text = f.read()

print(f"Transcript loaded: {len(transcript_text):,} characters")
print()

# Create video metadata
video_metadata = {
    'title': 'I Carried A UFO With My Helicopter - UFO Whistleblower Jake Barber',
    'url': 'https://www.youtube.com/watch?v=dnnpyNuPdXs',
    'uploader': 'American Alchemy',
    'duration': '03:04:10',
    'upload_date': '20241117',
    'view_count': 100000,
    'like_count': 5000,
    'channel_url': 'https://www.youtube.com/@AmericanAlchemy',
    'tags': ['UFO', 'whistleblower', 'Jake Barber'],
    'categories': ['News & Politics'],
    'description': 'Interview with UFO whistleblower Jake Barber',
    'chapters': [],
    'language': 'en',
    'whisper_model': 'large-v3',
    'analysis_mode': 'advanced'
}

print("Initializing Gemini 2.5 Pro summarizer...")
try:
    summarizer = ContentSummarizer(
        model='gemini-2.5-pro',
        output_dir='summaries'
    )
    print(f"✓ Gemini CLI detected and ready")
    print(f"✓ Context window: {summarizer.context_window:,} tokens")
    print(f"✓ Safe limit: {summarizer.max_input_tokens:,} tokens")
    print()

    # Generate summary
    print("Generating summary with Gemini 2.5 Pro...")
    print("This will test the full streaming integration")
    print()

    result = summarizer.summarize(
        transcript=transcript_text,
        video_metadata=video_metadata,
        analysis_mode='advanced',
        transcription_engine='elevenlabs'
    )

    print()
    print("=" * 80)
    print("✓ SUMMARY GENERATED SUCCESSFULLY")
    print("=" * 80)
    print()
    print(f"Output file: {result['output_file']}")
    print(f"Summary length: {len(result['summary']):,} characters")

except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
