# Short Video Studio — Codebase Map

## Scope
Dedicated MoneyPrinterTurbo-based short-video engine. This map reflects the current branch state after the subtitle and duration-gate changes.

## Runtime areas
- Production workflow: `.github/workflows/moneyprinterturbo.yml`.
- Orchestration workflow: `.github/workflows/daily-factory-orchestrator.yml`.
- Provider setup and routing: `scripts/configure_moneyprinter.py`, `scripts/free_model_router.py`, `scripts/avalai_client.py`.
- Content pipeline: `scripts/build_trending_batch.py`, `scripts/research_youtube_competitors.py`, `scripts/generate_seo_metadata.py`, `scripts/render_seo_thumbnails.py`.
- Subtitle processing: `scripts/add_persian_subtitles.py` writes Persian SRT and English/Persian VTT sidecars; it does not modify the MP4.
- Media validation: `scripts/validate_mpt_outputs.py` requires 60–120 seconds, vertical media, audio, Persian SRT and black/silence checks.
- Upload state: `scripts/upload_history.py`, `scripts/upload_four_private_youtube_tests.py`, `data/factory_state/`.
- Tests: `tests/`.
- Separate licensed-media engine: `viral_factory/`; it is not the MoneyPrinterTurbo short pipeline.

## Publication safety
- Scheduled upload step is private-only.
- Manual public upload still requires `workflow_dispatch` with `publish_four_public=true`.
- No public upload was performed in this work.
- Pending upload ledger entries are intentionally not retried blindly.

## Scheduling limitation
GitHub Actions schedules are evaluated from the repository default branch. The default branch is `main`, not this branch. Therefore this branch's cron declarations do not by themselves prove a daily scheduled run. A default-branch dispatcher change is required and was not made because `main` is protected by the user's explicit instruction.

## Known limitations
- Real MoneyPrinterTurbo rendering against the new 60–120 second gate remains untested.
- YouTube caption-track upload and processing confirmation are not implemented/verified.
- CI and unit tests are not equivalent to a complete generation, upload or caption end-to-end test.
