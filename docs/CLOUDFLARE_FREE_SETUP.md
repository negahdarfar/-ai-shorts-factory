# Cloudflare Workers AI free route

This factory can use the pinned Cloudflare Workers AI model `@cf/zai-org/glm-4.7-flash` without connecting the Android phone or Tailscale. It uses Cloudflare's OpenAI-compatible Chat Completions endpoint.

## Required account configuration

1. Use a Cloudflare account on the **Workers Free** plan. Do not upgrade to Workers Paid or enable paid inference for this workflow. On Workers Free, requests stop when the daily free allocation is exhausted; on Workers Paid, usage beyond the free allocation can be billed.
2. Open Cloudflare Dashboard → Workers AI → Use REST API → Create a Workers AI API Token. Use the Workers AI permissions required for inference.
3. Copy the Cloudflare Account ID from the dashboard.
4. In GitHub repository Settings → Secrets and variables → Actions → New repository secret, add:
   - `CLOUDFLARE_ACCOUNT_ID` = Account ID
   - `CLOUDFLARE_API_TOKEN` = API token
5. Optionally add repository variable `CLOUDFLARE_MODEL` with the exact value `@cf/zai-org/glm-4.7-flash`. The workflow pins this model by default and rejects other model IDs to avoid accidental paid routing.

Never paste the token into chat or commit it to the repository. Keep `ALLOW_NONFREE_LLM_FALLBACK` unset/false. If the free quota is exhausted, generation should stop safely; it must not switch to paid models.

Official references:
- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/
- https://developers.cloudflare.com/workers-ai/get-started/rest-api/
