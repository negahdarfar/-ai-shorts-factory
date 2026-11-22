# Koroush AI — viral-video-factory

This branch is an isolated implementation track for the viral-video-factory production engine.

## Safety defaults
- CI validates code only; it does not upload or publish videos.
- No secrets are read, printed, modified, or deleted by this branch's CI.
- YouTube publishing must remain opt-in and pass media quality gates first.
- Real media-generation and OAuth upload tests are not considered passed until a run produces an artifact and YouTube confirms its video ID/status.

## Shared quality gate
`koroush_core.quality` uses FFprobe to inspect file integrity, duration, video dimensions, codecs, and audio presence. The validator supports duration limits and portrait/landscape aspect checks.

## Current implementation status
- [x] Isolated branch created from the existing main branch.
- [x] Shared media-inspection and validation module added.
- [x] Unit tests for missing/empty media rejection added.
- [x] CI workflow added for compile, tests, and FFmpeg toolchain verification.
- [ ] Factory-specific scriptwriting, licensed media, English TTS, Persian RTL subtitles, rendering, SEO, and publication workflow.
- [ ] End-to-end generated-video test and private YouTube upload confirmation.

Do not mark this engine production-ready until the outstanding end-to-end checks are evidenced by workflow artifacts and upload confirmation.
