# Viral Video Studio — Codebase Map

## Scope
Standalone licensed-media engine targeting 120–600 second videos. Default output is 1920×1080 landscape; CLI supports 16:9, 9:16 and 1:1, with matching technical validation.

## Runtime areas
- CLI: `viral_factory/cli.py`.
- Dependencies: `viral_factory/requirements.txt`.
- Tests: `viral_factory/test_cli.py`.
- Workflow: `.github/workflows/viral-factory.yml`.
- Shared content QA: `scripts/evaluate_content_quality.py`.
- Translation helper: `scripts/translate_srt_to_persian.py`.

## Current pipeline
1. Discover eligible Wikimedia Commons video files.
2. Accept CC0, CC BY and public domain; reject NC, ND, unknown and ShareAlike.
3. Optionally collect YouTube most-popular metadata as research only. Snapshot includes views, age, views/hour and observation timestamp; channel baseline is not available from this endpoint.
4. Download an eligible Commons source and record source page, download URL, creator, credit, license name/URL, SHA-256 and UTC download timestamp.
5. Transcribe English speech with Faster-Whisper.
6. Select non-overlapping 120–600 second transcript windows ending at sentence punctuation; arbitrary evenly-spaced fallback was removed.
7. Render using FFmpeg in the selected aspect ratio.
8. Generate English/Persian SRT and VTT sidecars; Persian text is not burned into the MP4.
9. Emit source attribution, metadata, quality and run reports.
10. Manual private QA upload is available through `upload_private=true`; public publishing requires explicit manual `publish_public=true`. Scheduled runs never upload.

## Rights limitations
Commons metadata is not independent legal verification. ShareAlike is rejected until obligations are implemented and audited. The current candidate record is still not a complete human-reviewed legal rights determination.

## Scheduling limitation
GitHub scheduled workflows run only from the default branch (`main`). The viral branch cron does not independently prove daily execution. The current main-branch viral workflow is manual-only.

## Not yet verified
Real 4-minute rendering, full legal license review, private YouTube upload, YouTube caption-track upload/processing, and end-to-end provider failover.
