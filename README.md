# KOROUSH VIRAL SHORTS FACTORY — Short Video Studio

Dedicated engine for automated short-form YouTube production.

## What lives here
- MoneyPrinterTurbo-based Shorts generation and batch orchestration.
- Trend/topic research, competitor research, SEO metadata and thumbnail rendering.
- English content workflow with Persian subtitle tooling.
- Video validation, visual uniqueness checks, topic/upload history.
- YouTube analytics dashboard and weekly optimization.
- Shared AI provider routing and quality checks.
- An isolated `viral_factory/` package is present separately; see its own README.

## Main entry points
- `.github/workflows/moneyprinterturbo.yml` — primary Shorts production workflow.
- `.github/workflows/daily-factory-orchestrator.yml` — scheduled/manual orchestration.
- `scripts/build_trending_batch.py` — topic batch preparation.
- `scripts/generate_seo_metadata.py` — SEO metadata generation.
- `scripts/add_persian_subtitles.py` and `scripts/translate_srt_to_persian.py` — Persian subtitle tooling.
- `scripts/validate_mpt_outputs.py` — generated output validation.
- `scripts/youtube_analytics_report.py` and `scripts/weekly_optimization.py` — performance feedback.

## Repository map
See [docs/CODEBASE_MAP.md](docs/CODEBASE_MAP.md) for the file inventory, boundaries, and known workflow path inconsistencies.

## Safe changes
Preserve existing runtime logic and persistent state. Before moving any file, map imports, workflow paths, artifacts, caches, and tests. Keep public publishing opt-in during testing.

## Current limitation
Some workflow triggers still reference legacy branch names. These are documented in the codebase map and must be corrected as a separate, tested workflow-only change.
