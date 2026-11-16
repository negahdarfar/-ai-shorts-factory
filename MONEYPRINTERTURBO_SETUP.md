# MoneyPrinterTurbo-powered Shorts Factory

This branch uses the official **MoneyPrinterTurbo v1.3.10** engine (MIT license), fetched from its upstream repository during the workflow. It replaces the previous prototype that cut four unrelated clips from one random source.

Upstream: https://github.com/harry0703/MoneyPrinterTurbo

## What this version does
- Finds fresh topics from Google Trends RSS (US), remembers previously used topics, and refuses to reuse them in the next run.
- Creates one independent video task per topic (up to four per run).
- Uses Gemini for script generation, Pexels or Pixabay for topic-matched stock footage, and Microsoft Edge neural TTS for voiceover.
- Renders 9:16 vertical videos with word-by-word animated captions and background music.
- Upload is OFF during the quality test. Nothing is published to YouTube.

## Free-tier secrets
Repository Settings → Secrets and variables → Actions → New repository secret:
- `GEMINI_API_KEY`: Google AI Studio free-tier key: https://aistudio.google.com/apikey
- `PEXELS_API_KEY`: free stock-footage API key: https://www.pexels.com/api/
- `PIXABAY_API_KEY`: optional second free source: https://pixabay.com/api/docs/

At least one footage key is required. The workflow uses Pexels when available, otherwise Pixabay. Edge TTS needs no paid key. AI video models such as Seedance, MiniMax, WaveSpeed and OFox are paid services and are deliberately not selected.

Free API tiers have quotas and can change; this is not unlimited free AI video generation. The free pipeline uses licensed stock footage matched to the script, not newly synthesized photorealistic footage.

## YouTube connection test (manual and private only)
Add these repository Actions secrets after completing OAuth authorization:
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

The workflow has a manual `upload_private_test` switch. It defaults to `false`; normal quality runs and pull-request runs never upload. Only when explicitly enabled on a manual workflow run, the uploader sends exactly one validated MP4 to YouTube with `privacyStatus=private`. It does not publish publicly and does not upload all four videos.

To run a generation-only quality test, open Actions → MoneyPrinterTurbo Shorts Factory → Run workflow and leave `upload_private_test` unchecked. Download `moneyprinterturbo-quality-test` and inspect all four MP4s and their selected topics.

Only after the four outputs pass visual/topic review and the private connection test is confirmed should we discuss any broader publishing workflow or daily schedule.

## Publishing and monetization
Google OAuth projects left in External / Testing mode generally issue refresh tokens that expire after 7 days. Move beyond Testing only after reviewing Google's verification and publishing requirements; do not assume the current test token is permanent. Auto-publishing requires a separate publishing setup and valid account authorization. AI-generated/altered content must be disclosed where applicable. YouTube may reject monetization for repetitive or mass-produced low-value videos, so review and add original value before enabling automatic public uploads.