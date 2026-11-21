# YouTube Shorts Analytics Setup

The analytics workflow is read-only and does not upload or modify videos.

## Required repository secrets

- `YOUTUBE_CLIENT_ID` — existing Google OAuth client ID.
- `YOUTUBE_CLIENT_SECRET` — existing Google OAuth client secret.
- `YOUTUBE_ANALYTICS_REFRESH_TOKEN` — a separate refresh token authorized with the `yt-analytics.readonly` scope.

Do not replace the working upload refresh token. The analytics token is separate so a scope change cannot break publishing.

## Enable

1. In the Google Cloud project used by the channel, enable YouTube Analytics API.
2. Complete OAuth consent for the same YouTube channel and request `https://www.googleapis.com/auth/yt-analytics.readonly`.
3. Store the resulting refresh token as `YOUTUBE_ANALYTICS_REFRESH_TOKEN` in GitHub Actions secrets.
4. Run **YouTube Analytics** manually once to verify access. Scheduled analytics runs daily at 05:30 UTC (09:00 Iran time in UTC+03:30). Weekly optimization runs Monday at 06:30 UTC (10:00 Iran time) and downloads the latest completed analytics artifact.
5. The workflow uploads a 30-day artifact named `youtube-analytics-report`. The weekly optimization workflow runs after scheduled analytics and uploads `weekly-shorts-optimization`.

## Metrics and limitations

The report supports a 1-90 day lookback (default 28 days) and separates Shorts using YouTube Analytics `creatorContentType=SHORTS` and collects views, engaged views, average view duration, average percentage viewed, likes, comments, shares and subscribers gained.

Since YouTube changed public Shorts view counting, `views` includes plays/replays from the first frame. `engagedViews` is also recorded and is more useful for meaningful engagement comparisons. The ratio `engagedViews / views` is labelled as a directional proxy only; it is not the exact Studio "Stayed to watch" / "Viewed vs swiped away" metric.

The workflow does not claim that a particular hook or topic caused a result. The weekly report compares recent and prior windows and produces review recommendations rather than changing the publishing strategy automatically.
