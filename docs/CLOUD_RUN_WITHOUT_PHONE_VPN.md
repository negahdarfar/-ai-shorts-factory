# Running the Shorts factory without the phone VPN

The MoneyPrinterTurbo workflow can run in cloud mode without connecting GitHub Actions to the Android FreeLLMAPI gateway.

## Cloud mode (phone stays untouched)

- Leave the manual workflow input `use_phone_gateway` unchecked.
- Do not set the repository Actions variable `USE_PHONE_FREELLMAPI` to `true`.
- The workflow will not start Tailscale or contact the phone gateway.
- Cloud generation still requires a usable LLM route, a footage API key (`PEXELS_API_KEY` or `PIXABAY_API_KEY`), and `YOUTUBE_API_KEY` for competitor research. With the current free-only policy, generation safely stops if no explicitly permitted model provider is configured. No paid provider is silently enabled.

## Phone gateway mode

To use the Android gateway for a manual run, select `use_phone_gateway` in the workflow dispatch form. The phone must be online, Tailscale connected, and FreeLLMAPI running.

For scheduled runs only, an owner may deliberately set the Actions repository variable `USE_PHONE_FREELLMAPI=true`. Leave it unset or false to keep the phone out of the workflow.

## YouTube safety

Scheduled runs upload validated videos as **PRIVATE** QA drafts only. They do not automatically publish publicly. Public publishing is available only from a manual workflow dispatch when `publish_four_public` is explicitly selected. Private upload tests remain private.

## Required cloud credentials

Depending on the selected provider, configure the relevant Actions secrets:
- `PEXELS_API_KEY` or `PIXABAY_API_KEY`
- `YOUTUBE_API_KEY` (competitor research)
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` (OAuth upload)
- A supported LLM provider credential/configuration. The workflow's free-only guard remains enabled unless the repository owner deliberately changes the policy.

Never paste secret values into issues, pull requests, workflow inputs, or chat.
