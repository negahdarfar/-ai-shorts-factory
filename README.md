# KOROUSH VIRAL SHORTS FACTORY — Viral Video Studio

Dedicated, standalone engine for discovering reusable viral media and rendering vertical Shorts.

## What lives here
- `viral_factory/cli.py` — discovery, license checks, downloads, transcription, clip scoring, rendering, and upload commands.
- `viral_factory/requirements.txt` — isolated engine dependencies.
- `viral_factory/test_cli.py` — engine tests.
- `.github/workflows/viral-factory.yml` — GitHub Actions entry point.
- `scripts/evaluate_content_quality.py` — shared content-quality gate.

## Main workflow
Wikimedia Commons discovery → license/attribution filtering → optional YouTube trend metadata → selected asset download → Faster-Whisper transcription → hook/window scoring → FFmpeg vertical rendering → quality gate → optional YouTube upload.

## Local commands
```bash
python -m pip install -r viral_factory/requirements.txt
python viral_factory/cli.py discover --output-dir viral_factory/work
python viral_factory/cli.py process --candidate-index 0 --output-dir viral_factory/work --limit 4
```

## Important publishing warning
The workflow's `publish_public` input currently defaults to `true`, while the engine README says public upload is opt-in. Do not run a public workflow until this mismatch is reviewed and corrected. This documentation pass does not alter publishing behavior.

## Repository map
See [docs/CODEBASE_MAP.md](docs/CODEBASE_MAP.md) for the detailed inventory and safety boundaries.
