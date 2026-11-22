# AvalAI optional provider

AvalAI is integrated as an optional OpenAI-compatible text-model provider. It does not replace FreeLLMAPI, OpenRouter, Gemini, Cloudflare, local Ollama, FFmpeg, Edge TTS/eSpeak, Commons media discovery, or YouTube publishing.

## Safety and cost policy

- Credential: `AVALAI_API_KEY` (GitHub Actions Secret only).
- Base URL: `https://api.avalai.ir/v1` by default. AvalAI documents `https://api.avalapis.ir/v1` and `https://api.avalai.org/v1` as alternate domains.
- Chat route: `/chat/completions`.
- The provider is optional. Missing credentials do not break existing providers.
- The factory selects only models whose live `GET /models` catalogue explicitly marks them free or advertises exactly zero input and output prices. Unknown-price and paid models are excluded. Tier 0/account access is not treated as proof of zero price.
- Set `AVALAI_MODEL` to prefer a model ID only if that model is present and passes the free-price check. `auto` uses the task-ranked free candidates.
- No AvalAI SDK or paid package is added; the client uses Python standard library only.
- No API key is printed, committed, or written to artifacts. HTTP errors are reduced to safe status/type messages.

## Repository configuration

1. Open **Settings → Secrets and variables → Actions → Secrets**.
2. Add repository secret `AVALAI_API_KEY` with the API key from AvalAI.
3. Optionally add repository variable `AVALAI_BASE_URL`:
   - `https://api.avalai.ir/v1` (default)
   - `https://api.avalapis.ir/v1` (alternate domestic route)
   - `https://api.avalai.org/v1` (Cloudflare-backed international route)
4. Optionally add repository variable `AVALAI_MODEL`. Leave it as `auto` to discover all eligible free models automatically.

## Safe connection test

Run **Actions → AvalAI safe connection check → Run workflow**. This performs a catalogue-only authenticated `GET /models` request. It does not call Chat Completions, generate text, publish videos, or use the YouTube API. If the secret is missing, the workflow reports SKIPPED without making a network request.

## Integrated tasks

- Shorts: topic-aware English scripts and SEO title/description/tags.
- Shorts and long-form: Persian SRT translation while preserving cue order and timestamps.
- Long-form: English documentary script and storyboard generation.
- Content-quality evaluation is wired into the Shorts SEO, selected-clip, and long-form script workflows. It reports editorial scores but never verifies facts or authorizes publication.

## Free-provider fallback order

AvalAI is an optional route. Existing free routes remain in place (FreeLLMAPI, OpenRouter, approved Cloudflare free models, configured Gemini free tier, and local Ollama where enabled). If AvalAI is unavailable or has no explicitly free models, the existing configured free providers are tried. Local non-AI fallbacks remain drafts and do not bypass factual, rights, or publication gates.

## Important limitation

AvalAI's model catalogue and prices can change. The live catalogue check is the source of model eligibility; documentation examples, account tier, signup credits, and temporary promotions are not treated as a promise of ongoing free usage. A real model inference test is intentionally not part of the safe connection workflow.


## Rate-limit behavior

AvalAI documents tier-based RPM/RPD/TPM limits. A 429 response is reported as `AVALAI_CONNECTION_RATE_LIMITED`; it does not count as a successful authentication or model-catalogue check. The connection workflow uses only `GET /models`, and no inference request is sent during that check. See https://docs.avalai.org/en/rate-limits.
