# Viral Video Studio — Codebase Map

## Scope
Standalone licensed-media video engine; current target output is 120–600 seconds in 16:9 landscape.

## Runtime areas
- CLI: `viral_factory/cli.py`.
- Dependencies: `viral_factory/requirements.txt`.
- Tests: `viral_factory/test_cli.py`.
- Workflow: `.github/workflows/viral-factory.yml`.
- Shared quality gate: `scripts/evaluate_content_quality.py`.
- Translation helper: `scripts/translate_srt_to_persian.py`.

## Current pipeline
1. Discover eligible Wikimedia Commons video files.
2. Filter to CC0, CC BY and public domain; reject NC, ND, unknown and ShareAlike.
3. Optionally collect YouTube popular-video metadata as research only.
4. Download the selected Commons source and retain its attribution record.
5. Transcribe English speech with Faster-Whisper.
6. Select non-overlapping 120–600 second transcript windows.
7. Render 16:9 by default with FFmpeg.
8. Write English and Persian SRT sidecars and run technical validation.
9. Manual private QA upload is available through `upload_private=true`; public publishing requires explicit manual `publish_public=true`. Scheduled runs do not upload.

## Rights limitations
The current source record preserves source page, download URL, creator, credit and license label/URL. Per-file SHA-256 and download timestamp are not yet persisted in the rights record. Commons metadata does not independently prove legal rights. ShareAlike is rejected until obligations can be implemented and reviewed.

## Scheduling limitation
Cron workflows must exist on the default branch (`main`) to run on schedule. This branch alone cannot activate its cron. No main-branch changes were made.

## Not yet verified
Real 4-minute rendering, full legal license review, actual private YouTube upload, separate YouTube caption-track upload, caption processing, and end-to-end provider failover.
