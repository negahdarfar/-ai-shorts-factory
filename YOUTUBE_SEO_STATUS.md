# YouTube SEO and Documentary Factory — implementation status

## Implemented in this branch

### Shorts topic and SEO preparation
- Selects up to four non-repeated topics from Google Trends, with a curated fallback list.
- Drafts English metadata per topic with Gemini: primary/secondary keywords, title, description, hashtags, tags, pinned-comment prompt, search intent and thumbnail concept.
- Optionally researches a limited sample of recent public YouTube Shorts with YouTube Data API v3.
- Validates metadata fields, title/description limits, primary keyword presence, tags, hashtags and record count.
- Renders reviewable 1280x720 thumbnail draft images from the generated metadata using Pillow. These are typographic concept drafts, not finished topic-specific photographic artwork.

### YouTube publishing and channel data tools
- Existing uploader remains strictly PRIVATE QA and uploads exactly four videos only when the manual workflow input is selected.
- `apply_youtube_seo_metadata.py` can update title, description, tags and language for explicitly mapped video IDs using a reviewed JSON manifest. It never changes privacy status. It is intentionally not auto-run against public videos.
- `youtube_analytics_report.py` fetches read-only channel reports for views, watch time, average view duration/percentage and (when supported) impressions/CTR.
- The analytics script requires a refresh token consented for `yt-analytics.readonly`. Existing upload-only refresh tokens do not gain new scopes automatically; re-consent is required.
- Public publishing, scheduled publishing and automatic SEO writes are not enabled.

### Long-form assembly utilities
- `assemble_documentary.py` joins an ordered JSON list of video clips, normalizes them to 1080p landscape MP4, can replace clip audio with a narration track, and can burn an externally prepared UTF-8 Persian SRT file.
- `validate_chapters.py` checks that chapter timestamps start at 00:00, contain at least three chapters and increase strictly.
- These are assembly utilities, not yet a complete autonomous documentary creator. Clip generation, story continuity, fact-checking, Persian translation/timing, music licensing, chapter generation from the final timeline and final editorial approval still require integration and testing.

### CI and cost safeguards
- A lightweight pull-request CI workflow runs unit tests and Python syntax checks.
- The expensive MoneyPrinterTurbo generation job now runs only after a manual `workflow_dispatch`; opening/updating a PR no longer starts video generation.
- No daily schedule is enabled.

## Secrets and permissions

Existing Shorts generation:
- `GEMINI_API_KEY`
- At least one of `PEXELS_API_KEY` or `PIXABAY_API_KEY`

Optional public competitor research:
- `YOUTUBE_API_KEY` with YouTube Data API v3 enabled.

Existing private upload:
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN` with the upload scope.

Analytics:
- Re-authorize the channel and replace the refresh token with one granted `https://www.googleapis.com/auth/yt-analytics.readonly`.
- Do not paste OAuth tokens or client secrets into chat or commit them to the repository.

## Explicitly not complete yet

- Automatic VidoGrid/Grok generation with API key, quota tracking, polling/retries and continuity/reference-image management.
- Automated English documentary research, source verification, narration generation and long-form script approval.
- Automatic Persian subtitle translation, speech alignment and SRT quality checks.
- Full long-form pipeline orchestration from topic to final export.
- Reliable visual matching/continuity checks across generated clips.
- Full competitor channel/topic-gap analysis and Google Search SERP research.
- Real keyword search-volume/difficulty data; the public YouTube Data API does not expose these metrics.
- Applying metadata automatically to the four QA uploads (requires a trusted stable mapping from each output file to its topic and video ID).
- Automatic thumbnail upload through `thumbnails.set`; current thumbnails are local draft images only.
- Analytics-driven recommendation/optimization loop and channel dashboard.
- Public upload and scheduled publishing.

## Important platform constraints

Metadata can improve relevance and presentation, but cannot guarantee search ranking or recommendations. YouTube evaluates relevance and viewer response; tags are supporting metadata rather than a reliable growth lever. Do not stuff keywords or promise results.

YouTube Data API supports updating video metadata and setting thumbnails, but authorized writes require the appropriate OAuth permissions. Analytics reports require OAuth authorization; the `yt-analytics.readonly` scope is documented by Google. Sources:
- YouTube Data API videos resource: https://developers.google.com/youtube/data/reference/rest/v3/videos
- YouTube Analytics API reference: https://developers.google.com/youtube/analytics/reference
- Analytics authorization: https://developers.google.com/youtube/reporting/guides/authorization
- YouTube Search & Discovery: https://support.google.com/youtube/answer/11914225
- YouTube performance FAQ: https://support.google.com/youtube/answer/141805
- Google Video SEO best practices: https://developers.google.com/search/docs/appearance/video
- Google VideoObject structured data: https://developers.google.com/search/docs/appearance/structured-data/video

## Safe next steps

1. Run lightweight CI and correct any failing checks.
2. Manually run the existing four-video private QA workflow and inspect all four videos.
3. Add the optional YouTube API key if competitor research is desired.
4. Re-authorize OAuth for Analytics only when ready to connect private channel analytics.
5. Test the metadata updater against a private QA video and a manifest with an explicit video ID.
6. Test the documentary assembler with a short sample set and synchronized Persian SRT before using long productions.
7. Only after review and explicit approval, design a separate public-publishing/scheduling gate.
