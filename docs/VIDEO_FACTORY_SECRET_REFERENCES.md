# Video factory secret references

This file documents secret names referenced by the video workflows. Secret values must only be stored in GitHub Actions repository or environment secrets and must never be committed, printed, or copied into workflow artifacts.

## Existing video pipeline references
- GEMINI_API_KEY
- PEXELS_API_KEY
- PIXABAY_API_KEY
- CLOUDFLARE_ACCOUNT_ID
- CLOUDFLARE_API_TOKEN
- FREELLMAPI_BASE_URL
- FREELLMAPI_API_KEY
- FREELLMAPI_CLOUD_BASE_URL
- FREELLMAPI_CLOUD_API_KEY
- OMNIROUTE_API_KEY
- YOUTUBE_API_KEY
- YOUTUBE_CLIENT_ID
- YOUTUBE_CLIENT_SECRET
- YOUTUBE_REFRESH_TOKEN

## Analytics-only reference
- YOUTUBE_ANALYTICS_REFRESH_TOKEN

GITHUB_TOKEN is supplied automatically by GitHub Actions and is not a user-created repository secret.

## Important
The names above are code/workflow references, not a live inventory of configured secrets. Repository secrets are shared by workflows across branches; they are not branch-local and do not need to be copied when adding a branch. Confirm required names in Settings → Secrets and variables → Actions. Never paste secret values into issues, pull requests, chat, logs, or source files.
