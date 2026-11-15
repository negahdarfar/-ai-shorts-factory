# PurffleShorts engine (quality-test branch)

This branch replaces the old one-source/four-crops prototype with the MIT-licensed PurffleShorts engine, pinned to upstream commit `514fd2547227b98d951dfc1489fc8c7ce72f1b68`.

## Why this engine
- Topic → researched script → per-scene visuals → free neural voice → word-synced captions → vertical MP4.
- Topic sources include YouTube search suggestions, trends, Wikipedia and Reddit.
- Avoids cutting four unrelated moments from one random long video.
- Includes script review, format variety, footage crediting, history and duplicate-topic avoidance.
- Upload is deliberately OFF until sample videos pass review.

Upstream project: https://github.com/Chamanrajragu/purffle-shorts
License: MIT. The upstream source is installed at a pinned commit during the workflow; it is not copied or modified here.

## Free-tier setup needed for the first real test
In GitHub: Settings → Secrets and variables → Actions → New repository secret. Add:
- `GEMINI_API_KEY`: free-tier key from https://aistudio.google.com/apikey
- `PEXELS_API_KEY`: free API key from https://www.pexels.com/api/
- `PIXABAY_API_KEY`: optional second free footage source from https://pixabay.com/api/docs/

At least one of Pexels or Pixabay is required for reliable real footage. Microsoft Edge neural TTS needs no paid voice key. Free tiers have provider quotas and terms; no unlimited generation is promised.

## Run a quality test
Open Actions → Purffle Shorts Factory → Run workflow and choose 1, 2 or 4 videos. The default is four. It does not upload to YouTube. Download `purffle-shorts-quality-test` and inspect every MP4, script, caption and metadata file.

Only after visual quality and topic relevance are accepted should YouTube OAuth be configured and a daily schedule enabled.

## Important limits
- The first no-key demo is a sample render, not the full topic-research pipeline.
- YouTube auto-upload requires a separate Google Cloud project, YouTube Data API v3 and OAuth authorization for the channel.
- AI-generated content must be disclosed where required. Mass-produced or repetitive low-value videos can be ineligible for monetization.