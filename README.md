# KOROUSH — Viral Video Studio

Standalone, license-aware engine for producing 2–10 minute English-language videos from eligible source footage.

## Current implementation
- Discovers source video files on Wikimedia Commons and optionally collects YouTube most-popular metadata for topic research only.
- YouTube trend metadata is not downloaded or republished.
- Source candidates are filtered to CC0, CC BY and public-domain labels. NC, ND, unknown and ShareAlike licenses are rejected by default until their obligations are implemented and audited.
- Faster-Whisper transcribes English source audio; transcript windows are scored heuristically and selected without overlap.
- FFmpeg renders 120–600 second landscape 16:9 outputs by default. `--aspect` also accepts 9:16 or 1:1, but the current QA validator is deliberately strict for the required 16:9 output.
- English and Persian SRT sidecars are produced. Persian text is no longer burned into the MP4.
- Scheduled workflow runs may discover and render but never upload. Public upload is gated to an explicit manual workflow dispatch with `publish_public=true`.

## Local commands
```bash
python -m pip install -r viral_factory/requirements.txt
python viral_factory/cli.py discover --output-dir viral_factory/work
python viral_factory/cli.py process --candidate-index auto --limit 2 --model tiny --aspect 16:9 --output-dir viral_factory/work
python -m unittest discover -s viral_factory -p 'test_*.py' -v
```
A candidate source must contain enough English speech to yield at least one complete 120-second clip. No short-clip fallback is used.

## Rights and trend-data boundaries
- A popular YouTube video is a research signal, not a reuse license.
- Each downloaded Commons candidate retains its source page, license label/URL, creator and credit metadata.
- This implementation does not yet capture every requested provenance field (including a verified per-file hash/date ledger) or establish channel-baseline performance.
- A license label returned by Commons is metadata, not independent legal verification. Review the source page and terms before commercial publication.

## Scheduling and publishing
GitHub Actions schedules run only from the default branch (`main`). The cron declaration in this specialized branch does not prove it will execute daily. Public upload is manual-only in the current workflow. No upload was performed during this work.

## Known limits
- Real 4-minute render, rights review, YouTube private upload and caption-track upload have not been executed.
- The current publish command still needs a private-upload mode and a verified YouTube caption-track path before it can satisfy the complete private-upload requirement.
- Faster-Whisper CPU processing and FFmpeg rendering can be slow and resource-intensive.
