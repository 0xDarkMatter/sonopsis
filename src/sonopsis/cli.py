"""
Sonopsis CLI - agent-first typer application.

stdout carries data (file paths, JSON envelopes); all progress and chrome go
to stderr. Engine internals print progress via plain print(), so commands
that run the pipeline redirect sys.stdout into stderr for the duration and
write their result to the real stdout afterwards.
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import default_engine, load_config
from .credentials import PROVIDERS, CredentialStore, auth_overview, export_to_env
from .models import DEFAULT_API_MODEL, DEFAULT_CLI_MODEL, MODELS, available_models
from .summarizer import claude_cli_available

app = typer.Typer(
    name="sonopsis",
    help="Video/audio summariser - download, transcribe, summarise.",
    no_args_is_help=True,
)
console = Console(stderr=True)

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_AUTH_REQUIRED = 2
EXIT_NOT_FOUND = 3
EXIT_VALIDATION = 4

ENGINES = ["parakeet", "parakeet-dia", "whisper", "whisperx", "elevenlabs", "openai"]
ENGINE_EXTRAS = {  # engine -> uv extra(s) that provide it
    "parakeet": ["parakeet"],
    "parakeet-dia": ["parakeet", "diarize"],
    "whisper": ["whisper"],
    "whisperx": ["whisper", "diarize"],
    "elevenlabs": ["elevenlabs"],
    "openai": [],
}
URL_RE = re.compile(r"https?://|youtu\.?be", re.IGNORECASE)


def _output_json(data) -> None:
    print(json.dumps(data, indent=2, default=str))


def _error(message: str, code: str = "ERROR", exit_code: int = EXIT_ERROR,
           details=None, as_json: bool = False):
    if as_json:
        error_obj = {"error": {"code": code, "message": message}}
        if details:
            error_obj["error"]["details"] = details
        _output_json(error_obj)
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(exit_code)


def _require_summarization_backend(as_json: bool = False):
    import os
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("OPENROUTER_API_KEY") or claude_cli_available()):
        _error(
            "No summarization backend. Run `sonopsis auth login <provider>` or "
            "install the Claude Code CLI (https://claude.com/claude-code).",
            "AUTH_REQUIRED", EXIT_AUTH_REQUIRED, as_json=as_json,
        )


def _startup():
    """Load .env then backfill missing keys from the keyring."""
    load_dotenv(override=True)
    export_to_env()


def _default_model(config: dict) -> str:
    import os
    return (os.getenv("SUMMARY_MODEL") or config["defaults"].get("summary_model")
            or (DEFAULT_CLI_MODEL if claude_cli_available() else DEFAULT_API_MODEL))


def version_callback(value: bool):
    if value:
        print(f"sonopsis {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[Optional[bool], typer.Option(
        "--version", "-V", callback=version_callback, is_eager=True,
        help="Show version and exit.")] = None,
):
    """Video/audio summariser - download, transcribe, summarise."""


# ---------------------------------------------------------------------------
# summarise / transcribe
# ---------------------------------------------------------------------------

def _engine_option_default() -> str:
    return default_engine(load_config()["defaults"].get("transcription_engine"))


@app.command("summarise")
@app.command("summarize", hidden=True)
def summarise(
    url: Annotated[str, typer.Argument(help="YouTube video or playlist URL")],
    engine: Annotated[Optional[str], typer.Option(
        "--engine", "-e", help=f"Transcription engine: {', '.join(ENGINES)}")] = None,
    model: Annotated[Optional[str], typer.Option(
        "--model", "-m", help="Summarization model (claude-cli, claude-sonnet-4-6, gpt-5.1, ...)")] = None,
    whisper_model: Annotated[str, typer.Option(
        "--whisper-model", help="Whisper size: tiny|base|small|medium|large")] = "base",
    analysis_mode: Annotated[str, typer.Option(
        "--analysis-mode", help="basic (5 sections) or advanced (9 sections)")] = "basic",
    num_speakers: Annotated[Optional[int], typer.Option(
        "--num-speakers", help="Known speaker count for diarizing engines")] = None,
    auto_speakers: Annotated[bool, typer.Option(
        "--auto-speakers", help="Infer speaker count from metadata (high confidence only)")] = False,
    keep_files: Annotated[bool, typer.Option(
        "--keep-files", help="Keep downloaded audio")] = False,
    skip_existing: Annotated[bool, typer.Option(
        "--skip-existing", help="Skip playlist videos that already have a summary")] = False,
    start_from: Annotated[int, typer.Option(
        "--start-from", help="Playlist: start at video N")] = 1,
    json_output: Annotated[bool, typer.Option("--json", help="Emit {data, meta} JSON on stdout")] = False,
):
    """Download, transcribe and summarise a video or playlist.

    Examples:
        sonopsis summarise https://youtu.be/dQw4w9WgXcQ
        sonopsis summarise URL --engine parakeet-dia --auto-speakers --json
    """
    _startup()
    from .downloader import YouTubeDownloader
    from .pipeline import find_existing_summary, process_video

    if engine and engine not in ENGINES:
        _error(f"Unknown engine '{engine}'. Choose from: {', '.join(ENGINES)}",
               "VALIDATION_ERROR", EXIT_VALIDATION, as_json=json_output)
    if not URL_RE.search(url):
        _error("That doesn't look like a YouTube URL.", "VALIDATION_ERROR",
               EXIT_VALIDATION, {"url": url}, as_json=json_output)
    _require_summarization_backend(json_output)

    config = load_config()
    paths = config["paths"]
    engine = engine or _engine_option_default()
    model = model or _default_model(config)

    common = dict(
        whisper_model=whisper_model, gpt_model=model, analysis_mode=analysis_mode,
        keep_files=keep_files, transcription_engine=engine,
        num_speakers=num_speakers, auto_speakers=auto_speakers,
        downloads_dir=paths["downloads"], transcripts_dir=paths["transcripts"],
        summaries_dir=paths["summaries"],
    )

    results = []
    # Engine internals print progress to stdout; route all of it to stderr so
    # stdout stays a clean data channel
    with contextlib.redirect_stdout(sys.stderr):
        if YouTubeDownloader.is_playlist(url):
            videos = YouTubeDownloader(output_dir=paths["downloads"]).get_playlist_videos(url)
            for idx, video in enumerate(videos, 1):
                if idx < start_from:
                    continue
                if skip_existing and find_existing_summary(video["url"], paths["summaries"]):
                    results.append({"success": True, "url": video["url"], "skipped": True})
                    continue
                results.append(process_video(video["url"], video_num=idx,
                                             total_videos=len(videos), **common))
        else:
            results.append(process_video(url, **common))

    succeeded = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    data = [{k: r.get(k) for k in ("success", "skipped", "url", "title",
                                   "transcript_file", "summary_file") if k in r}
            for r in results]

    if json_output:
        _output_json({"data": data if len(data) > 1 else data[0],
                      "meta": {"count": len(results), "succeeded": len(succeeded),
                               "failed": len(failed), "engine": engine, "model": model}})
    else:
        for r in succeeded:
            if r.get("summary_file"):
                print(r["summary_file"])  # data channel: produced artifact paths
        console.print(f"[green]{len(succeeded)} succeeded[/green]"
                      + (f", [red]{len(failed)} failed[/red]" if failed else ""))

    if failed:
        raise typer.Exit(EXIT_ERROR)


@app.command("transcribe")
def transcribe(
    source: Annotated[str, typer.Argument(help="YouTube URL or local audio file")],
    engine: Annotated[Optional[str], typer.Option("--engine", "-e")] = None,
    whisper_model: Annotated[str, typer.Option("--whisper-model")] = "base",
    num_speakers: Annotated[Optional[int], typer.Option("--num-speakers")] = None,
    keep_files: Annotated[bool, typer.Option("--keep-files")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
):
    """Download (if a URL) and transcribe - no summarization.

    Examples:
        sonopsis transcribe https://youtu.be/dQw4w9WgXcQ --engine parakeet
        sonopsis transcribe recording.mp3 --engine parakeet-dia --num-speakers 2 --json
    """
    _startup()
    import os
    from .downloader import YouTubeDownloader
    from .transcriber import AudioTranscriber

    if engine and engine not in ENGINES:
        _error(f"Unknown engine '{engine}'. Choose from: {', '.join(ENGINES)}",
               "VALIDATION_ERROR", EXIT_VALIDATION, as_json=json_output)
    config = load_config()
    paths = config["paths"]
    engine = engine or _engine_option_default()

    with contextlib.redirect_stdout(sys.stderr):
        if URL_RE.search(source):
            video = YouTubeDownloader(output_dir=paths["downloads"]).download_video(source)
            audio_file = video["audio_file"]
            reused = video.get("reused_existing", False)
        elif Path(source).exists():
            audio_file, reused = source, True
        else:
            _error(f"Source not found: {source}", "NOT_FOUND", EXIT_NOT_FOUND,
                   as_json=json_output)

        transcriber = AudioTranscriber(
            model_name=whisper_model, output_dir=paths["transcripts"], engine=engine,
            hf_token=os.getenv("HF_TOKEN"),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            num_speakers=num_speakers,
        )
        try:
            result = transcriber.transcribe(str(audio_file))
        except Exception as e:
            _error(str(e), "ERROR", EXIT_ERROR, as_json=json_output)
        if not keep_files and not reused:
            Path(audio_file).unlink(missing_ok=True)

    if json_output:
        _output_json({"data": {"transcript_file": result["text_file"],
                               "language": result["language"],
                               "characters": len(result["text"])},
                      "meta": {"engine": engine}})
    else:
        print(result["text_file"])


@app.command("tui")
def tui_command():
    """Launch the interactive menu interface."""
    from .tui import main as tui_main
    tui_main()


# ---------------------------------------------------------------------------
# engines
# ---------------------------------------------------------------------------

engines_app = typer.Typer(help="Transcription engine packs")
app.add_typer(engines_app, name="engines")


def _engine_status() -> list:
    import importlib.util
    import os
    have = {
        "onnx_asr": importlib.util.find_spec("onnx_asr") is not None,
        "whisper": importlib.util.find_spec("whisper") is not None,
        "pyannote": importlib.util.find_spec("pyannote") is not None,
        "elevenlabs_sdk": importlib.util.find_spec("elevenlabs") is not None,
    }
    rows = [
        {"engine": "parakeet", "installed": have["onnx_asr"], "type": "local",
         "needs": "" if have["onnx_asr"] else "sonopsis engines install parakeet"},
        {"engine": "parakeet-dia", "installed": have["onnx_asr"] and have["pyannote"],
         "type": "local", "needs": ("HF_TOKEN" if not os.getenv("HF_TOKEN") else "")
         if (have["onnx_asr"] and have["pyannote"]) else "sonopsis engines install diarize"},
        {"engine": "whisper", "installed": have["whisper"], "type": "local",
         "needs": "" if have["whisper"] else "sonopsis engines install whisper"},
        {"engine": "whisperx", "installed": have["whisper"] and have["pyannote"],
         "type": "local", "needs": "HF_TOKEN" if not os.getenv("HF_TOKEN") else ""},
        {"engine": "elevenlabs", "installed": have["elevenlabs_sdk"], "type": "cloud",
         "needs": "ELEVENLABS_API_KEY" if not os.getenv("ELEVENLABS_API_KEY") else ""},
        {"engine": "openai", "installed": True, "type": "cloud",
         "needs": "OPENAI_API_KEY" if not os.getenv("OPENAI_API_KEY") else ""},
    ]
    default = _engine_option_default()
    for row in rows:
        row["default"] = row["engine"] == default
    return rows


@engines_app.command("list")
def engines_list(json_output: Annotated[bool, typer.Option("--json")] = False):
    """Show engines, installation state and what each still needs."""
    _startup()
    rows = _engine_status()
    if json_output:
        _output_json({"data": rows, "meta": {"count": len(rows)}})
        return
    table = Table(title="Transcription engines")
    for col in ("engine", "type", "installed", "needs", "default"):
        table.add_column(col)
    for r in rows:
        table.add_row(r["engine"], r["type"],
                      "[green]yes[/green]" if r["installed"] else "[red]no[/red]",
                      r["needs"] or "-", "*" if r["default"] else "")
    console.print(table)


@engines_app.command("install")
def engines_install(
    pack: Annotated[str, typer.Argument(help="parakeet | whisper | diarize | elevenlabs")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
):
    """Install an engine pack (runs `uv sync --inexact --extra <pack>`)."""
    valid = {"parakeet", "whisper", "diarize", "elevenlabs"}
    if pack not in valid:
        _error(f"Unknown pack '{pack}'. Choose from: {', '.join(sorted(valid))}",
               "VALIDATION_ERROR", EXIT_VALIDATION, as_json=json_output)
    console.print(f"Installing engine pack [bold]{pack}[/bold]...")
    result = subprocess.run(["uv", "sync", "--inexact", "--extra", pack],
                            capture_output=True, text=True)
    if result.returncode != 0:
        _error(f"uv sync failed: {result.stderr[-400:]}", "ERROR", EXIT_ERROR,
               as_json=json_output)
    if json_output:
        _output_json({"data": {"installed": pack}, "meta": {}})
    else:
        console.print(f"[green]Installed[/green] {pack}")


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------

models_app = typer.Typer(help="Summarization models")
app.add_typer(models_app, name="models")


@models_app.command("list")
def models_list(
    all_models: Annotated[bool, typer.Option("--all", help="Include models without a configured backend")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
):
    """List summarization models (default: only usable ones)."""
    _startup()
    usable = set(available_models(claude_cli=claude_cli_available()))
    rows = []
    for model_id, info in MODELS.items():
        if info.get("hidden"):
            continue
        if not all_models and model_id not in usable:
            continue
        rows.append({"model": model_id, "provider": info["provider"],
                     "quality": info["quality"], "cost": info["cost"],
                     "available": model_id in usable})
    if json_output:
        _output_json({"data": rows, "meta": {"count": len(rows)}})
        return
    table = Table(title="Summarization models")
    for col in ("model", "provider", "quality", "cost", "available"):
        table.add_column(col)
    for r in rows:
        table.add_row(r["model"], r["provider"], r["quality"], r["cost"],
                      "[green]yes[/green]" if r["available"] else "[red]no[/red]")
    console.print(table)


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

auth_app = typer.Typer(help="Credential management (env > .env > keyring)")
app.add_typer(auth_app, name="auth")


@auth_app.command("status")
def auth_status(json_output: Annotated[bool, typer.Option("--json")] = False):
    """Show which providers are configured and where the credential lives."""
    _startup()
    overview = auth_overview()
    if json_output:
        _output_json({"data": overview, "meta": {"count": len(overview)}})
        return
    table = Table(title="Authentication status")
    for col in ("provider", "configured", "source", "unlocks"):
        table.add_column(col)
    for provider, row in overview.items():
        table.add_row(provider,
                      "[green]yes[/green]" if row["configured"] else "[red]no[/red]",
                      row["source"] or "-", row["unlocks"])
    console.print(table)


@auth_app.command("login")
def auth_login(
    provider: Annotated[str, typer.Argument(help=f"One of: {', '.join(PROVIDERS)}")],
    key: Annotated[Optional[str], typer.Option("--key", "-k", help="Credential value (prompted if omitted)")] = None,
):
    """Store a provider credential in the OS keyring."""
    if provider not in PROVIDERS:
        _error(f"Unknown provider '{provider}'. Choose from: {', '.join(PROVIDERS)}",
               "VALIDATION_ERROR", EXIT_VALIDATION)
    if not key:
        key = typer.prompt(f"{PROVIDERS[provider][0]}", hide_input=True)
    try:
        CredentialStore(provider).set(key)
    except RuntimeError as e:
        _error(str(e), "ERROR", EXIT_ERROR)
    console.print(f"[green]Stored[/green] {provider} credential in the keyring")


@auth_app.command("logout")
def auth_logout(
    provider: Annotated[str, typer.Argument(help=f"One of: {', '.join(PROVIDERS)}")],
):
    """Remove a provider credential from the OS keyring."""
    if provider not in PROVIDERS:
        _error(f"Unknown provider '{provider}'. Choose from: {', '.join(PROVIDERS)}",
               "VALIDATION_ERROR", EXIT_VALIDATION)
    if CredentialStore(provider).delete():
        console.print(f"[green]Removed[/green] {provider} credential from the keyring")
    else:
        console.print(f"No keyring credential for {provider} "
                      "(env/.env values are not managed by logout)")


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

config_app = typer.Typer(help="Configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(json_output: Annotated[bool, typer.Option("--json")] = False):
    """Show the effective configuration (defaults merged with config.yaml)."""
    config = load_config()
    config["defaults"]["transcription_engine_resolved"] = _engine_option_default()
    if json_output:
        _output_json({"data": config, "meta": {}})
    else:
        console.print_json(json.dumps(config, default=str))


# ---------------------------------------------------------------------------
# entry point with legacy-argv shim
# ---------------------------------------------------------------------------

def run() -> None:
    """Console-script entry point.

    Back-compat shims so pre-0.3.0 invocations keep working:
    - `sonopsis <URL> [flags]` -> `sonopsis summarise <URL> [flags]`
    - engine shortcut flags (--parakeet, --openai, ...) -> --engine <name>
    - old flag spellings --transcription-engine/--gpt-model -> --engine/--model
    """
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    argv = sys.argv[1:]
    if argv and URL_RE.search(argv[0]):
        argv = ["summarise"] + argv
    rewritten = []
    for arg in argv:
        if arg == "--transcription-engine":
            rewritten.append("--engine")
        elif arg == "--gpt-model":
            rewritten.append("--model")
        elif arg.startswith("--") and arg[2:] in ENGINES:
            rewritten += ["--engine", arg[2:]]
        else:
            rewritten.append(arg)
    sys.argv = [sys.argv[0]] + rewritten
    app()


if __name__ == "__main__":
    run()
