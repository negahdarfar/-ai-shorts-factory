# KOROUSH — Long Video Studio

Research-led English documentary production and technical quality assurance.

## Current implementation
- Topic discovery, evidence dossier generation and evidence audit.
- AI-assisted chapter plan and English narration generation.
- Wikimedia Commons media discovery with a rights ledger.
- Mixed image/video storyboard assembly and FFmpeg 1920×1080 rendering.
- Persian SRT translation and technical validation.
- Persian subtitles are separate sidecar files by default; burn-in is optional and disabled in the render workflow by default.
- Long-form QA enforces 16:9 HD media, audio and a 10–30 minute output window in the main render validator.

## Workflow entry points
- `.github/workflows/longform-render.yml` — research, planning, source discovery, narration, subtitles, rendering and QA.
- `.github/workflows/longform-studio.yml` — manual assembly and QA from prepared clips, narration and Persian SRT.

## Current limitations
- YouTube private upload and YouTube caption-track upload are not implemented/verified.
- The legacy manual assembly workflow accepts pre-prepared files; it does not independently perform the full research and media discovery pipeline.
- No 12-minute real render or private upload was executed during this work.
- GitHub scheduled workflows run only from the default branch; these manual workflows do not establish a daily schedule.
- Rights metadata checks do not independently prove ownership or legal permission; human review remains required.
