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

## Run the quality test
1. Open Actions → MoneyPrinterTurbo Shorts Factory → Run workflow.
2. Choose `4` videos.
3. Wait for the run to finish, then download `moneyprinterturbo-quality-test`.
4. Inspect all four MP4s and their selected topics. The test does not upload anything.

Only after the four outputs pass visual/topic review should we configure publishing credentials and enable a daily schedule.

## Publishing and monetization
Auto-publishing requires a separate publishing setup and valid account authorization. AI-generated/altered content must be disclosed where applicable. YouTube may reject monetization for repetitive or mass-produced low-value videos, so review and add original value before enabling automatic public uploads.