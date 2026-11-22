# KOROUSH AI Video Factory — three production branches

This repository is organized around exactly three production tracks. Keep production code isolated by branch; share only tested, reusable components.

| Branch | Factory | Primary output |
|---|---|---|
| `shorts-factory` | Shorts Factory | English 45–60 second vertical videos with Persian RTL subtitles, SEO metadata, QC and scheduled YouTube publishing |
| `viral-video-factory` | Viral Video Factory | Trend-led, distinctive short-form videos with source/licence checks, hook analysis and performance feedback |
| `longform-studio` | Longform Studio | Research-led English documentaries, long-form narration, Persian subtitles, chapters and 16:9 delivery |

## Shared engineering principles

- Free-first provider routing. A provider is treated as free only when its free tier is explicitly documented or its catalogue exposes zero input/output pricing. Free quotas and availability are not unlimited or guaranteed.
- Local-first optional tools: Ollama, FFmpeg, Whisper and the AVGen renderer bridge. Hosted GitHub runners cannot reach a developer's localhost; local providers must be explicitly configured or exposed through a secure reachable endpoint.
- English narration and video content; Persian subtitles must preserve timing, use RTL-safe shaping and be checked before publication.
- Licensed footage only. Preserve source URLs, creators, licence names and attribution obligations.
- Every rendered file passes technical validation before upload. Public publishing must not bypass failed checks.
- SHA-256 upload history and topic history prevent duplicate publication and unsafe retries.
- A weekly read-only API catalogue and GitHub project scout searches for free-first integrations without reading secrets, cloning repositories or executing third-party code.
- Secrets are read only at runtime. Never print, copy into artifacts, or commit secret values.

## Current verified state

- All three production branches have isolated CI and a shared FFprobe-based quality module.
- Shorts has the most complete production workflow, including per-topic rendering retries, 9:16 media validation, Persian subtitle checks, duplicate protection, analytics and weekly optimization.
- Viral has a separate Wikimedia Commons discovery/rendering pipeline, conservative licence filtering, English-only Whisper transcription, Persian SRT translation/burn-in, FFprobe QC, SHA-256 upload idempotency and a default-branch dispatch scheduler. Original narration/TTS and real end-to-end publication evidence are still outstanding.
- Longform has an assembly workflow, English voiceover handling, Noto Naskh Arabic subtitle burn-in, chapter validation, 16:9/duration/audio QC, free-provider routing and shared upload safeguards. Automated research, long-form script generation, licensed scene discovery and TTS remain outstanding.
- Shorts retains its daily public-release workflow. Viral's scheduler is ready but runs only after `shorts-factory` becomes the repository default branch. Longform remains assembly/QC-only and does not auto-publish.
- A passing unit/CI run is not evidence of a completed real-world video render or YouTube upload. End-to-end readiness requires an actual rendered artifact and a confirmed YouTube video ID.

## Branch cleanup

After all legacy capabilities have been reviewed and the three production branches are ready, set `shorts-factory` as the repository default branch. The guarded **Archive and remove non-production branches** workflow creates recovery tags for every other branch before deleting its branch ref. Do not run it until you are satisfied that the migration is complete.
