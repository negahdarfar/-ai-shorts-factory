# Gemini free-tier route

The MoneyPrinterTurbo workflow can use the official Gemini API directly without FreeLLMAPI.

## GitHub configuration

In repository Settings → Secrets and variables → Actions:

1. Add repository secret `GEMINI_API_KEY` with the API key created in Google AI Studio.
2. Add repository variable `GEMINI_FREE_TIER_ENABLED` with the exact value `true`.
3. Keep `ALLOW_NONFREE_LLM_FALLBACK` unset or `false`. The Gemini route is selected only when the explicit free-tier flag is true; this does not authorize paid fallback providers.

The workflow already passes both values to its configuration, SEO, and subtitle stages. No FreeLLMAPI cloud URL/key is needed for the MoneyPrinterTurbo Gemini route.

## Route priority

1. Pinned Cloudflare Workers AI free route, if its account ID and token are configured.
2. FreeLLMAPI only if its catalogue explicitly marks a model free.
3. OpenRouter only if its live catalogue explicitly marks a model free.
4. Gemini only when `GEMINI_FREE_TIER_ENABLED=true` and `GEMINI_API_KEY` is present.
5. Any other OmniRoute fallback is allowed only when `ALLOW_NONFREE_LLM_FALLBACK=true`; leave this false for a zero-cost project.

Gemini quotas are limited and can change by model, region, and account. This workflow does not guarantee unlimited or uninterrupted free inference. Check the current Gemini API pricing and rate limits before increasing batch size.

## Official links

- Google AI Studio API keys: https://aistudio.google.com/app/apikey
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits

Never paste the API key into chat or commit it to the repository.
