# Koroush AI — longform-studio

This branch is the dedicated long-form documentary production track.

## Safety defaults
- CI and the assembly workflow do not publish to YouTube.
- No secrets are read, printed, modified, or deleted by the validation workflow.
- A documentary must pass FFprobe, duration, 16:9, audio and Persian SRT checks before it is treated as a valid render.
- The assembler refuses to silently truncate an English voiceover when the supplied visual timeline is too short.
- A passing unit test is not evidence of a real documentary render or a successful YouTube upload.

## Implemented building blocks
- [x] Isolated production branch and shared FFprobe quality module.
- [x] FFmpeg documentary assembler with ordered clips, optional English narration and burned Persian subtitles.
- [x] Voiceover loudness normalization and duration-vs-visual-timeline guard.
- [x] Noto Naskh Arabic subtitle typography for Persian captions.
- [x] Longform media validator: minimum duration, 16:9 resolution, video/audio streams, Persian SRT timing and subtitle coverage.
- [x] YouTube chapter timestamp validator.
- [x] Manual Longform Studio assembly workflow with downloadable MP4 and QC report.
- [x] Shared free-model routing, local Ollama option, upload-idempotency helpers and local renderer bridge.
- [x] Regression tests for subtitle and documentary media validation.

## Still required before production readiness
- [ ] Automated topic research with traceable, credible source references.
- [ ] Long-form English script and chapter generation with fact-checking.
- [ ] Free/appropriately licensed footage discovery and per-scene matching.
- [ ] Automated English TTS and accurate word-level subtitle alignment/translation.
- [ ] Thumbnail and YouTube metadata generation.
- [ ] Safe OAuth upload, public scheduling, analytics and end-to-end tests using a real generated documentary.

The current workflow is an assembly-and-QC stage. It requires the ordered clip manifest, narration audio and Persian SRT to be supplied as repository files; it is not yet the complete research-to-publication factory.
