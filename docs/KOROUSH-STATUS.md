# Koroush AI — shorts-factory

This is the primary production branch and the most complete factory in the repository.

## Production pipeline implemented
- [x] English short-form scripts constrained to 120–145 words and 45–60 second output.
- [x] Vertical 9:16 generation through the pinned MoneyPrinterTurbo engine.
- [x] Configurable batch size from 4 to 10 videos per run. Manual runs select `video_count`; scheduled runs use `SHORTS_DAILY_VIDEO_COUNT` repository variable and default to 4.
- [x] Free-first model routing with Gemini, Cloudflare and configured free OpenAI-compatible gateways; paid fallback is disabled by default.
- [x] Optional private Android FreeLLMAPI gateway, local Ollama support and local AVGen renderer bridge.
- [x] English narration, Persian RTL subtitle translation and burn-in, with cue and media validation.
- [x] Topic research, competitor metadata, SEO titles/descriptions/tags, thumbnail drafts and distinct visual-search terms.
- [x] Retry handling for transient failures and incomplete model batches.
- [x] FFprobe checks for duration, codecs, audio/video streams and vertical dimensions.
- [x] Visual uniqueness comparison across generated videos.
- [x] SHA-256 upload idempotency, pending-upload reconciliation and topic-history duplicate guards.
- [x] Public YouTube scheduling with staggered release slots; up to ten videos are spaced two hours apart.
- [x] Read-only weekly API catalogue and open-source project discovery.
- [x] YouTube analytics, weekly optimization report and dashboard workflow.

## Safety and operational boundaries
- Public uploads happen only after script, subtitle, media, visual-uniqueness and metadata checks pass.
- Scheduled public release uses private uploads with future YouTube `publishAt` timestamps.
- The daily batch defaults to four videos. Increasing to 10 can exceed free-provider quotas or GitHub Actions usage; free tiers are not unlimited.
- Ollama and other local services are opt-in. A GitHub-hosted runner cannot access a developer's localhost without a secure reachable endpoint.
- CI does not read, print, modify or delete repository secrets.
- A passing CI run does not prove a real video render or successful YouTube upload. End-to-end readiness still requires a real artifact and confirmed YouTube video IDs.

## Remaining work
- [ ] Run and inspect a real 4-video batch end to end, including Persian subtitle visual review.
- [ ] Confirm YouTube OAuth upload and scheduled publication with returned video IDs.
- [ ] Tune provider fallback and batch sizing using actual quota/latency measurements.
- [ ] Verify daily analytics and weekly optimization with real channel data.

Do not claim unlimited free generation or production readiness until the end-to-end evidence above exists.
