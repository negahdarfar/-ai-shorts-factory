# KOROUSH VIRAL SHORTS FACTORY — Long Video Studio

Dedicated engine for research-led long-form documentary production and technical quality assurance.

## What lives here
- Research discovery and evidence dossier validation.
- AI-assisted documentary plan and chapter narration.
- Wikimedia Commons visual discovery with source and license provenance.
- Rights-ledger validation.
- Mixed image/video storyboard assembly and FFmpeg rendering.
- English narration with Persian subtitle generation/translation.
- Duration, chapter, audio, subtitle, and final-output validation.

## Workflow entry points
- `.github/workflows/longform-render.yml` — research, planning, source discovery, narration/subtitles, rendering and QA.
- `.github/workflows/longform-studio.yml` — manual assembly and QA from prepared clips, narration, and Persian SRT.

## Main guide
See [docs/LONGFORM_STUDIO.md](docs/LONGFORM_STUDIO.md) for input formats and operating instructions.

## Repository map
See [docs/CODEBASE_MAP.md](docs/CODEBASE_MAP.md) for the file inventory and module boundaries.

## Important boundary
These workflows provide rendering and QA paths; do not assume YouTube upload is implemented or verified here. Rights metadata checks do not independently prove ownership, and citation-structure checks do not independently prove factual accuracy.
