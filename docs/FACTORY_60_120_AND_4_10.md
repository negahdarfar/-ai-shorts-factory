# KOROUSH VIRAL SHORTS FACTORY — 60-120s / 4-10 batch

## Production targets

- Each final MP4 must be 60-120 seconds.
- Output must be vertical 9:16 and at least 720x1280; 1080x1920 receives the preferred quality score.
- Narration scripts must contain 155-270 words; the generation prompt targets 210-230 words. Final duration is checked from the rendered MP4, not inferred from word count.
- A daily batch contains 4-10 distinct Shorts. The workflow refuses values outside this range.
- Quality validation must pass before the upload step can run.

## Set the daily batch size

For scheduled production, add a GitHub Actions repository variable:

- `DAILY_SHORTS_COUNT`: integer from 4 through 10; defaults to 4 if unset.

For manual workflow dispatch, select `daily_count` from 4 through 10. The preserved four-topic test batch is only compatible with a count of four.

## Free-only model routing

The workflow uses Gemini 3.8 Flash Standard Free Tier first when `GEMINI_API_KEY` is configured. The `GEMINI_FREE_TIER_ENABLED` variable defaults to true because the Standard tier is listed as free; set it to false to disable Gemini. Free-tier limits can still cause rate-limit errors.

Fallback order for SEO generation is:

1. Gemini 3.8 Flash Standard Free Tier.
2. An explicitly verified-free FreeLLMAPI model.
3. The pinned Cloudflare Workers AI model.
4. An explicitly verified-free OpenRouter model.

`ALLOW_NONFREE_LLM_FALLBACK` remains false by default. Unknown-price or paid models are not enabled automatically. Free providers can be rate-limited or unavailable; if no provider returns validated content, the batch fails closed and is not published.

## Durable duplicate prevention

The factory stores:

- `data/factory_state/seen_topics.json`
- `data/factory_state/published_topics.json`
- `data/factory_state/upload_history.json`

The runtime Actions cache is merged with these repository files before discovery and after production. The uploader records each file's SHA-256 before the YouTube API call as a `pending` record, then marks it `completed` after receiving a video ID. A completed file is skipped on rerun. A pending record blocks blind retries and requires checking YouTube Studio first.

The state contains topic names, file hashes, video IDs, titles and upload URLs only; it must never contain OAuth tokens or API keys. Repository state is public because this repository is public.

## Quality checks

The technical gate checks file integrity, duplicate hashes, video/audio streams, 9:16 ratio, minimum resolution, duration, Persian subtitle timing/text, detected black frames, detected silence, and a per-video quality score. This does not prove factual accuracy, copyright clearance or creative originality; those checks remain separate.

## YouTube Analytics

Analytics uses a separate `YOUTUBE_ANALYTICS_REFRESH_TOKEN` with `yt-analytics.readonly` scope. It does not replace the working upload token. See [YOUTUBE_ANALYTICS_SETUP.md](YOUTUBE_ANALYTICS_SETUP.md).
