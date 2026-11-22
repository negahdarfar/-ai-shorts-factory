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

Create a rights ledger (default: `data/longform/rights.json`) with one object per clip. Example:

```json
[
  {
    "asset": "assets/longform/scene-01.mp4",
    "source_url": "https://example.org/original-source",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": "Creator name — source title"
  },
  {
    "asset": "assets/longform/scene-02.mp4",
    "source_url": "https://example.org/owned-footage-record",
    "license": "owned",
    "license_url": "https://example.org/rights-document",
    "attribution": "Original footage produced by our team",
    "rights_holder": "Rights holder name"
  }
]
```

Accepted license families: Public Domain/CC0, CC BY, CC BY-SA (requires `share_alike_acknowledged: true`), and footage marked `owned` with a named `rights_holder`. NC, ND, unknown, or incomplete records fail closed. Each record must include HTTPS source and license/evidence URLs plus attribution. A passing ledger checks metadata completeness; it does not independently prove that a claim is true or that the source actually grants the stated rights.

Optional inputs:
- Persian UTF-8 SRT file, for example `assets/longform/subtitles.fa.srt`
- Narration audio, for example `assets/longform/narration.wav`
- Burn subtitles: enabled only when an SRT path is supplied

## Run

Open **Actions → Koroush Longform Studio - render and QA → Run workflow** on the `longform-studio` branch. Supply the manifest path and optional assets. The default minimum duration is 480 seconds (8 minutes).

The workflow:
1. Validates that all inputs exist and remain inside the repository checkout.
2. Requires an exact rights-ledger record for every clip and rejects unclear/restricted licenses.
3. Normalizes clips to 1920×1080, 30 fps, H.264/AAC and joins them in manifest order.
4. Optionally replaces the clip audio with narration and burns the Persian subtitles into the video.
5. Requires a 16:9 output, at least 1280×720, an audio stream, and the configured minimum duration.
6. Uploads the MP4 and JSON QA report as a 14-day Actions artifact.

## Important limitations

- This workflow assembles supplied footage; it does not yet research a topic, generate a verified factual script, synthesize narration, or acquire licensed footage automatically.
- No YouTube upload or public publishing is performed by this workflow.
- A passed technical QA or rights-metadata report is not legal advice, proof of ownership, factuality review, editorial review, or a guarantee of audience retention.
- GitHub-hosted runners have time, storage, and artifact limits. Large footage collections may exceed those limits.
