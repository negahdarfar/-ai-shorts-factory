# Long Video Studio — Codebase Map

## Scope
This branch owns the research-led long-form documentary workflow, storyboard rendering, narration, Persian subtitles, rights checks, and technical QA.

## Runtime areas
- Research discovery: `scripts/discover_topic_sources.py`, `scripts/collect_research_sources.py`, `scripts/extract_research_pages.py`.
- Evidence validation: `scripts/build_research_dossier.py`, `scripts/audit_research_evidence.py`.
- Planning and narration: `scripts/generate_longform_plan.py`, `scripts/generate_narration_audio.py`.
- Media discovery and rights: `scripts/discover_commons_media.py`, `scripts/validate_rights_ledger.py`.
- Storyboard and rendering: `scripts/assemble_storyboard.py`, `scripts/assemble_documentary.py`.
- Quality gates: `scripts/validate_longform.py`, `scripts/validate_documentary.py`, `scripts/validate_chapters.py`.
- Workflow entry points: `.github/workflows/longform-render.yml`, `.github/workflows/longform-studio.yml`.
- Main operating guide: `docs/LONGFORM_STUDIO.md`.
- Input/state schemas: `data/longform/`.
- Automated tests: `tests/test_*research*`, `tests/test_*storyboard*`, `tests/test_*longform*`, `tests/test_*rights*`, plus shared pipeline tests.

## Workflow distinction
- `longform-render.yml` is the research → evidence → plan/media → narration/subtitle → render/QA workflow.
- `longform-studio.yml` is a separate manual assembly/QA workflow for an already prepared clip manifest, narration, and Persian SRT.
- Neither workflow should be described as a verified automatic YouTube publishing pipeline based only on its current render-and-QA steps.

## Safety and rights boundary
- Every used source asset must have a corresponding rights record.
- Reject unknown, incomplete, NC, and ND licenses.
- Preserve attribution, source URL, and license URL.
- A metadata validation pass does not independently establish copyright ownership or factual truth.
- Unverified and disputed claims must not be presented as established facts.

## Refactor boundary
This pass is documentation-only. Research, planning, rendering, rights validation, workflow behavior, dependencies, and state files are unchanged.
