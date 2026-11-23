# Long Video Studio — Codebase Map

## Scope
Research-led long-form documentary workflow, storyboard rendering, English narration, Persian subtitles, rights checks and technical QA. Target duration is 600–1800 seconds.

## Runtime areas
- Research discovery: `scripts/discover_topic_sources.py`, `scripts/collect_research_sources.py`, `scripts/extract_research_pages.py`.
- Evidence validation: `scripts/build_research_dossier.py`, `scripts/audit_research_evidence.py`.
- Planning and narration: `scripts/generate_longform_plan.py`, `scripts/generate_narration_audio.py`.
- Media discovery and rights: `scripts/discover_commons_media.py`, `scripts/validate_rights_ledger.py`.
- Storyboard and rendering: `scripts/assemble_storyboard.py`, `scripts/assemble_documentary.py`.
- Subtitle validation/conversion: `scripts/validate_documentary.py`, `scripts/srt_to_vtt.py`, `scripts/validate_chapters.py`.
- Quality gate: `scripts/validate_longform.py`, shared `koroush_core/quality.py`.
- Workflow entry points: `.github/workflows/longform-render.yml`, `.github/workflows/longform-studio.yml`.
- Main operating guide: `docs/LONGFORM_STUDIO.md`.
- Input/state schemas: `data/longform/`.
- Automated tests: research, storyboard, longform, rights, subtitles and shared pipeline tests.

## Workflow distinction
- `longform-render.yml` is the research → evidence → plan/media → English narration/Persian translation → render/QA workflow.
- `longform-studio.yml` is a separate manual assembly/QA workflow for an already prepared clip manifest, narration and Persian SRT.
- Neither workflow is a verified automatic YouTube publishing pipeline. Private video upload and caption-track upload are not implemented.

## Safety and rights boundary
- Every used source asset must have a corresponding rights record.
- Reject unknown, incomplete, NC and ND licenses.
- Preserve attribution, source URL and license URL.
- A metadata validation pass does not independently establish copyright ownership or factual truth.
- Unverified and disputed claims must not be presented as established facts.

## Known limitations
- The shared code under `koroush_core/` is still duplicated across branch snapshots; it has not yet been extracted into a separately versioned package consumed by all three engines.
- Python dependencies and FFmpeg are not yet fully hash-pinned or SBOM-audited; see `docs/DEPENDENCY_REVIEW.md`.
- No production-duration render or YouTube private upload was executed in this work.
