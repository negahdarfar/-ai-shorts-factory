# Longform Studio

This branch contains a manual render-and-QA path for long-form documentary videos.

## Inputs

1. Commit source clips to the repository and create a UTF-8 JSON manifest, for example:

```json
[
  "assets/longform/scene-01.mp4",
  "assets/longform/scene-02.mp4",
  "assets/longform/scene-03.mp4"
]
```

Paths are resolved from the repository root. Every clip must exist inside the checkout.
Only use footage, music, images, and narration that you own or are licensed to use. Keep source URLs, license identifiers, attribution text, and any ShareAlike obligations in a separate rights ledger before publication. The render workflow does not independently prove copyright ownership.

Optional inputs:
- Persian UTF-8 SRT file, for example `assets/longform/subtitles.fa.srt`
- Narration audio, for example `assets/longform/narration.wav`
- Burn subtitles: enabled only when an SRT path is supplied

## Run

Open **Actions → Koroush Longform Studio - render and QA → Run workflow** on the `longform-studio` branch. Supply the manifest path and optional assets. The default minimum duration is 480 seconds (8 minutes).

The workflow:
1. Validates that all inputs exist and remain inside the repository checkout.
2. Normalizes clips to 1920×1080, 30 fps, H.264/AAC and joins them in manifest order.
3. Optionally replaces the clip audio with narration and burns the Persian subtitles into the video.
4. Requires a 16:9 output, at least 1280×720, an audio stream, and the configured minimum duration.
5. Uploads the MP4 and JSON QA report as a 14-day Actions artifact.

## Important limitations

- This workflow assembles supplied footage; it does not yet research a topic, generate a verified factual script, synthesize narration, or acquire licensed footage automatically.
- No YouTube upload or public publishing is performed by this workflow.
- A passed technical QA report is not a legal-rights review, factuality review, editorial review, or guarantee of audience retention.
- GitHub-hosted runners have time, storage, and artifact limits. Large footage collections may exceed those limits.
