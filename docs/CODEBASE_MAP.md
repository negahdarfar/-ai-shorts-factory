# Short Video Studio — Codebase Map

## Scope
Dedicated MoneyPrinterTurbo-based short-video engine. This map reflects the current branch state after the subtitle and duration-gate changes.

## Runtime areas
- Production workflow: `.github/workflows/moneyprinterturbo.yml`.
- Branch-local orchestration workflow: `.github/workflows/daily-factory-orchestrator.yml` (not present on default branch `main`).
- Provider setup and routing: `scripts/configure_moneyprinter.py`, `scripts/free_model_router.py`, `scripts/avalai_client.py`.
- Content pipeline: `scripts/build_trending_batch.py`, `scripts/research_youtube_competitors.py`, `scripts/generate_seo_metadata.py`, `scripts/render_seo_thumbnails.py`.
- Subtitle processing: `scripts/add_persian_subtitles.py` writes Persian SRT and English/Persian VTT sidecars; it does not modify the MP4.
- Media validation: `scripts/validate_mpt_outputs.py` requires 60–120 seconds, 1080×1920 vertical media, audio, English/Persian SRT+VTT sidecars, valid cue timing and black/silence checks.
- Upload state: `scripts/upload_history.py`, `scripts/upload_four_private_youtube_tests.py`, `data/factory_state/`.
- Tests: `tests/`.
- Separate licensed-media engine: `viral_factory/`; it is not the MoneyPrinterTurbo short pipeline.

## Publication safety
- This branch's schedule step is private-only; the separate active `main` workflow still has a daily schedule that can create staggered PUBLIC releases. The observed 2026-11-22 schedule failed before upload, but the next successful run could reach that step.
- Manual public upload still requires `workflow_dispatch` with `publish_four_public=true`.
- No public upload was performed by this assistant; `main` was left unchanged pending approval.
- Pending upload ledger entries are intentionally not retried blindly.

## Scheduling limitation
GitHub Actions schedules run from the default branch. No dispatcher for this specialist branch is present on `main`; this branch's cron is not active. The separate legacy MoneyPrinterTurbo workflow on `main` is scheduled daily and can queue staggered PUBLIC releases when its earlier steps succeed. This branch's safer workflow changes do not alter that main-branch workflow.

## Known limitations
- Real MoneyPrinterTurbo rendering against the new 60–120 second gate remains untested.
- YouTube caption-track upload and processing confirmation are not implemented/verified.
- CI and unit tests are not equivalent to a complete generation, upload or caption end-to-end test.
