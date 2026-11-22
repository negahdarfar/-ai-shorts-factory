# Viral Video Studio — Codebase Map

## Scope
This branch owns the standalone, license-aware viral-media discovery and Shorts rendering engine.

## Runtime areas
- Main implementation: `viral_factory/cli.py`.
- Engine dependencies: `viral_factory/requirements.txt`.
- Engine tests: `viral_factory/test_cli.py`.
- User guide: `viral_factory/README.md`.
- Workflow: `.github/workflows/viral-factory.yml`.
- Shared content-quality gate: `scripts/evaluate_content_quality.py`.
- Shared YouTube upload/history and SEO helpers: `scripts/upload_history.py`, `scripts/upload_youtube_thumbnails.py`, `scripts/generate_seo_metadata.py`.
- Optional model/provider clients and routing: `scripts/free_model_router.py`, `scripts/avalai_client.py`.
- Persistent candidate/topic data: `data/`.

## Current documented pipeline
1. Discover video media on Wikimedia Commons.
2. Filter by supported reuse-license metadata and retain source attribution.
3. Optionally collect YouTube most-popular metadata (metadata research only).
4. Download a selected eligible Commons asset.
5. Transcribe English audio with Faster-Whisper.
6. Score transcript windows and render vertical clips with FFmpeg.
7. Run content-quality checks and optionally upload through YouTube OAuth.

## Important configuration mismatch
- The workflow input `publish_public` currently defaults to `true`.
- The engine README describes public publishing as opt-in and false by default.
- Scheduled workflow execution also follows a separate publishing condition.
Treat public publishing as a risk until the workflow and README are reconciled. This pass intentionally does not change either.

## Safety and license boundary
- Never treat YouTube trend metadata as permission to download or republish a YouTube video.
- Preserve source page, license URL, creator attribution, and asset history.
- Fail closed for unclear, non-commercial, or no-derivatives licenses.
- Keep upload disabled during tests and require explicit authorization before public release.

## Refactor boundary
This pass is documentation-only. The CLI, workflow, dependencies, upload behavior, and source/license checks are unchanged.
