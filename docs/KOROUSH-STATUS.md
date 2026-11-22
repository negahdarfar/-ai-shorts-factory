# Koroush AI — viral-video-factory

This branch is the dedicated trend-led short-video track. It is isolated from the Shorts Factory workflow.

## Safety defaults
- Public publishing remains explicit opt-in through the workflow input; scheduled public publishing is not enabled yet.
- The process rejects non-English source audio, unapproved licences, invalid vertical video, and clips without Persian subtitles.
- Source page, creator/credit and licence information are retained for attribution.
- SHA-256 upload history prevents duplicate uploads and blocks blind retries of pending uploads.
- CI never reads, prints, modifies or deletes YouTube secrets.
- A CI pass is not evidence of a real rendered video or a confirmed YouTube upload.

## Implemented
- [x] Wikimedia Commons video discovery with a conservative CC0 / CC BY / public-domain allowlist; non-commercial, no-derivatives and share-alike licences are excluded.
- [x] Source host, content type, download size and licence revalidation before download.
- [x] Local faster-whisper transcription with English-language enforcement.
- [x] Hook/question/number scoring and non-overlapping 20–58 second clip selection.
- [x] Per-clip English SRT timing derived from Whisper segments.
- [x] Persian translation through the configured Gemini free tier, with timing/cue preservation.
- [x] Persian subtitle burn-in using Noto Naskh Arabic typography.
- [x] FFprobe checks for 9:16 resolution, audio/video streams and duration before publication.
- [x] Idempotent public upload ledger and retained source attribution.
- [x] Dedicated CI coverage for the isolated Viral Factory and shared production modules.

## Still required
- [ ] Original English narration/TTS and more substantial editorial transformation beyond source-audio clips.
- [ ] Cross-run source-history persistence and automated candidate selection.
- [ ] Real end-to-end render artifact and private/public upload confirmation.
- [ ] Analytics-driven weekly optimization and automated public schedule after end-to-end validation.

Do not describe the factory as production-ready until a real video artifact, Persian subtitle burn-in and confirmed YouTube upload have been tested.
