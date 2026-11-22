# Short Video Studio — Codebase Map

## Scope
This branch is the dedicated short-form production engine. This document maps the current repository layout; it does not change runtime behavior.

## Runtime areas
- Root pipeline: `main.py`, `transcribe.py`, `clip_selector.py`, `viral_selector.py`, `video_editor.py`, `download_video.py`, `source_discovery.py`.
- Production orchestration: `.github/workflows/moneyprinterturbo.yml`, `.github/workflows/daily-factory-orchestrator.yml`.
- AI/provider integration: `scripts/free_model_router.py`, `scripts/configure_moneyprinter.py`, `scripts/avalai_client.py`, `scripts/api_intelligence.py`.
- Content pipeline: `scripts/build_trending_batch.py`, `scripts/research_youtube_competitors.py`, `scripts/generate_seo_metadata.py`, `scripts/apply_youtube_seo_metadata.py`, `scripts/render_seo_thumbnails.py`.
- Persian subtitles: `scripts/add_persian_subtitles.py`, `scripts/translate_srt_to_persian.py`, `scripts/translate_subtitles_free.py`.
- Quality and state: `scripts/evaluate_content_quality.py`, `scripts/validate_mpt_outputs.py`, `scripts/validate_seo_metadata.py`, `scripts/validate_visual_uniqueness.py`, `scripts/topic_history.py`, `scripts/upload_history.py`, `data/factory_state/`.
- Analytics: `scripts/youtube_analytics_report.py`, `scripts/build_factory_dashboard.py`, `scripts/weekly_optimization.py`.
- Tests: `tests/`; shared quality helpers: `koroush_core/`.
- Isolated licensed-media engine: `viral_factory/` (kept separate from the Shorts/MoneyPrinterTurbo pipeline).

## Safe operating rules
1. Do not move or rename runtime files until every Python import, workflow path, cache path, artifact path, and documented command has been mapped.
2. Do not edit provider credentials or GitHub Secrets from code changes.
3. Keep public upload opt-in for manual runs and require explicit validation gates.
4. Preserve generated state files and upload history.
5. Run compile, unit tests, workflow syntax checks, and a dry-run before any runtime refactor.

## Known path/trigger inconsistencies to resolve in a separate approved fix
- `koroush-ci.yml` watches the legacy `shorts-factory` branch name, not this branch name.
- `daily-factory-orchestrator.yml` dispatches Viral Factory using the legacy `viral-video-factory` ref.
- `moneyprinterturbo.yml` has a pull-request trigger scoped to `shorts-factory`.
These are recorded here only; workflow files have not been modified.

## Refactor boundary
This pass is documentation-only. No Python source, workflow, dependency, secret, or production-state file is changed.
