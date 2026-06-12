"""
End-to-end tests: real YouTube download, real Whisper transcription, real
Claude Code CLI summarization.

These hit the network and real backends, so they only run when explicitly
requested:

    RUN_E2E=1 uv run --extra dev --extra whisper pytest tests/e2e -v

Test video: "Me at the zoo" (jNQXAC9IVRw) - the first YouTube video, 19s long,
chosen so transcription and summarization complete in well under a minute.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
# E2E tests exercise real backends - pick up API keys from the project .env
load_dotenv(PROJECT_ROOT / ".env")
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
TEST_VIDEO_ID = "jNQXAC9IVRw"

e2e = pytest.mark.skipif(
    not os.getenv("RUN_E2E"),
    reason="E2E tests need network + real backends; set RUN_E2E=1 to run",
)


def _backend_available() -> bool:
    return bool(shutil.which("claude") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))


@e2e
class TestFullPipeline:
    def test_download_transcribe_summarize(self, tmp_path):
        """The whole pipeline on a real 19-second video with whisper tiny +
        the Claude Code CLI (haiku alias for speed)."""
        if not _backend_available():
            pytest.skip("No summarization backend configured")

        downloads = tmp_path / "downloads"
        transcripts = tmp_path / "transcripts"
        summaries = tmp_path / "summaries"

        # Point output dirs at tmp via a scratch config.yaml is not possible
        # through the CLI yet, so drive the pipeline directly.
        sys.path.insert(0, str(PROJECT_ROOT))
        from utils.pipeline import process_video

        model = "claude-cli/haiku" if shutil.which("claude") else (
            "claude-haiku-4-5-20251001" if os.getenv("ANTHROPIC_API_KEY") else "gpt-4o-mini"
        )

        result = process_video(
            TEST_VIDEO_URL,
            whisper_model="tiny",
            gpt_model=model,
            analysis_mode="basic",
            keep_files=True,
            transcription_engine="whisper",
            downloads_dir=str(downloads),
            transcripts_dir=str(transcripts),
            summaries_dir=str(summaries),
        )

        assert result['success'], f"Pipeline failed: {result.get('error')}"

        # Audio was downloaded with the canonical naming scheme
        audio_files = list(downloads.glob(f"YT_{TEST_VIDEO_ID}_*.mp3"))
        assert audio_files, "Downloaded audio file missing"

        # Transcript exists and contains the famous line about elephants
        transcript_path = Path(result['transcript_file'])
        assert transcript_path.exists()
        transcript_text = transcript_path.read_text(encoding="utf-8")
        assert "elephant" in transcript_text.lower(), \
            f"Transcript doesn't mention elephants: {transcript_text[:300]}"

        # Summary exists, has the metadata header and real content
        summary_path = Path(result['summary_file'])
        assert summary_path.exists()
        assert summary_path.name.startswith(f"YT_{TEST_VIDEO_ID}_")
        summary_text = summary_path.read_text(encoding="utf-8")
        assert "# Video Summary:" in summary_text
        assert "### Processing Information" in summary_text
        assert len(summary_text) > 500, "Summary suspiciously short"

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
    def test_openai_diarize_engine(self, tmp_path):
        """Real gpt-4o-transcribe-diarize call - validates the diarized_json
        response contract the unit tests only mock."""
        sys.path.insert(0, str(PROJECT_ROOT))
        from utils.downloader import YouTubeDownloader
        from utils.transcriber import AudioTranscriber

        downloader = YouTubeDownloader(output_dir=str(tmp_path / "downloads"))
        video = downloader.download_video(TEST_VIDEO_URL)

        transcriber = AudioTranscriber(output_dir=str(tmp_path / "transcripts"), engine="openai")
        result = transcriber.transcribe(video['audio_file'])

        assert "elephant" in result['text'].lower()
        assert Path(result['text_file']).exists()

    def test_cached_audio_reused_when_noninteractive(self, tmp_path):
        """A second download of the same video must auto-reuse the cached
        audio without blocking on input() when stdin is not a terminal."""
        downloads = tmp_path / "downloads"

        # Seed the cache with a real download via a subprocess whose stdin is
        # closed - proving the non-interactive path never prompts.
        script = (
            "import sys; sys.path.insert(0, r'{root}')\n"
            "from utils.downloader import YouTubeDownloader\n"
            "d = YouTubeDownloader(output_dir=r'{out}')\n"
            "r1 = d.download_video('{url}')\n"
            "assert not r1['reused_existing']\n"
            "r2 = d.download_video('{url}')\n"
            "assert r2['reused_existing'], 'second call should reuse cached audio'\n"
            "print('REUSE-OK')\n"
        ).format(root=PROJECT_ROOT, out=downloads, url=TEST_VIDEO_URL)

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=300,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"stderr: {result.stderr[-500:]}"
        assert "REUSE-OK" in result.stdout
