# KOROUSH Viral Factory (isolated)

Standalone, manually triggered content discovery and Shorts rendering.

## Isolation
- All application code is under \`viral_factory/\`.
- Its only workflow is \`.github/workflows/viral-factory.yml\`.
- Does not edit or import the legacy root-level Python pipeline.
- No schedule and no automatic publishing.
- Public upload is an explicit workflow input, false by default.
- Existing YouTube OAuth secrets are reused only when publishing is explicitly enabled.

## Features
1. Searches Wikimedia Commons for video files and accepts only identified CC0, CC BY, CC BY-SA or public-domain material.
2. Optionally reads YouTube most-popular metadata if \`YOUTUBE_API_KEY\` exists. This is trend research only; it does not download YouTube videos.
3. Downloads only a selected Wikimedia Commons candidate and rechecks its source host and license.
4. Transcribes locally with faster-whisper, scores transcript windows for hooks/questions/numbers, and renders vertical 9:16 MP4 clips with FFmpeg.
5. Optionally uploads rendered clips using the existing YouTube OAuth refresh-token secrets, with attribution in the description.

## Local run
Python 3.11+ and FFmpeg/ffprobe are required.

\`\`\`bash
python -m pip install -r viral_factory/requirements.txt
python viral_factory/cli.py discover --output-dir viral_factory/work
python viral_factory/cli.py process --candidate-index 0 --output-dir viral_factory/work --limit 4
\`\`\`

## GitHub Actions
Actions → **KOROUSH Viral Factory (standalone)** → Run workflow.

- \`discover\`: discovery report only.
- \`process\`: discovers eligible material, downloads the selected Commons candidate and renders Shorts.
- \`publish_public=false\` by default. Set true only when public upload is intended.

Existing secrets used for publishing:
- \`YOUTUBE_CLIENT_ID\`
- \`YOUTUBE_CLIENT_SECRET\`
- \`YOUTUBE_REFRESH_TOKEN\`

Optional: \`YOUTUBE_API_KEY\` for YouTube trend metadata. Commons discovery works without it.

A Creative Commons license may require attribution; source and license details are included in the description. The project deliberately does not scrape/download TikTok, Instagram, X, Reddit or ordinary YouTube videos. It does not guarantee YouTube monetization eligibility.
