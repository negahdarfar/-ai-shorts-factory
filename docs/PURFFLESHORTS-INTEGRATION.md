# PurffleShorts integration

The factory can run the upstream MIT-licensed PurffleShorts 3.1.0 renderer as an additional, manually dispatched Shorts engine. The upstream source is installed at the pinned commit:

`Chamanrajragu/purffle-shorts@514fd2547227b98d951dfc1489fc8c7ce72f1b68`

## Run

GitHub → Actions → **PurffleShorts Video Engine** → Run workflow.

- Choose 1–4 videos.
- Public YouTube upload is enabled by default; turn it off for render-only tests.
- The private Android FreeLLMAPI route requires the phone server to be running and reachable over Tailscale. The cloud route is used only when its two cloud secrets are configured and the phone route is not selected.
- The workflow is manual-only. It does not create a second scheduled publishing job or change the existing MoneyPrinterTurbo schedule.

## Existing repository secrets reused

No new secret names are required:

- Cloud LLM: `FREELLMAPI_CLOUD_BASE_URL`, `FREELLMAPI_CLOUD_API_KEY`
- Optional private phone gateway: `FREELLMAPI_BASE_URL`, `FREELLMAPI_API_KEY`, `TAILSCALE_AUTHKEY`
- YouTube OAuth: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`
- Optional footage providers: `PEXELS_API_KEY`, `PIXABAY_API_KEY`

The workflow creates a temporary local OAuth token file from the existing refresh-token secrets. It is never committed to Git. Before installing/running the renderer, a short HTTP preflight checks whether the selected FreeLLMAPI host responds; an unreachable host fails fast instead of spending several minutes on model retries.

## Behavior and limits

- Uses FreeLLMAPI as a custom OpenAI-compatible provider, with no paid LLM fallback configured. There is no automatic free-provider fallback: a separate provider requires a reachable endpoint and valid credentials.
- Uses Edge TTS, FFmpeg, and Pexels/Pixabay when credentials are available.
- Generates 45-second, 9:16 videos and sets YouTube synthetic-media disclosure to true.
- The upstream project supports short-form generation and long-video clipping. It is not a one-hour text-to-video renderer; long-form output needs a separate assembly workflow.
- GitHub-hosted runners are ephemeral. This workflow runs only when manually dispatched and does not promise continuous 24/7 generation.
- Review the GitHub Actions logs and `purffle-shorts-output` artifact after a run. No live YouTube upload is performed merely by adding this integration.
