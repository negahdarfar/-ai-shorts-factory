# FreeLLMAPI on Android + private GitHub Actions access

This project uses the official upstream FreeLLMAPI router on the Android phone, then lets GitHub Actions reach it over a private Tailscale network. No VPS is required. The phone must stay powered, online, and awake while a workflow is using it.

Official upstream: https://github.com/tashfeenahmed/freellmapi  
Official Android instructions: https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/install/02-android-termux.md  
Tailscale GitHub Action: https://tailscale.com/docs/integrations/github/github-action

## 1. Install FreeLLMAPI on Android

1. Install **Termux from F-Droid** (not the outdated Play Store build).
2. Install the **Tailscale** Android app and sign in to your Tailscale account.
3. Open Termux and run:

```bash
pkg update
pkg upgrade -y
pkg install -y nodejs-lts git
node --version
git clone https://github.com/tashfeenahmed/freellmapi.git
cd freellmapi
npm install --no-audit --no-fund
```

Node must be 22.13 or newer. Start the dashboard/API so the phone can accept private Tailscale connections:

```bash
HOST=0.0.0.0 npm run dev:lan
```

Open `http://localhost:5173` on the phone. The API is at `http://localhost:3001/v1`.

## 2. Add provider keys inside FreeLLMAPI

In the dashboard:

1. Open **Keys** and add API keys for providers whose free tier you are eligible to use.
2. Open **Models / Fallback Chain** and select a chain of free models you have actually enabled.
3. Disable any paid model/provider routes if you want to avoid accidental paid fallback.
4. Run a short test in the built-in Playground.
5. Copy the single unified `freellmapi-...` API key from the Keys page.

FreeLLMAPI is a router, not free inference credits. Each upstream provider has its own quota, eligibility, terms and availability. Check each provider's terms before using its output in a monetized YouTube channel. Do not enable providers whose terms prohibit your intended use.

## 3. Keep the Android service awake

In a second Termux session (or after starting the server), run:

```bash
pkg install -y termux-api
termux-wake-lock
```

Disable Android battery optimization for Termux and keep the phone connected to power and Wi-Fi. Android can still stop background processes; if the phone sleeps or loses internet, the GitHub job cannot reach this gateway.

To stop the server, return to the Termux session and press Ctrl+C. Release the wake lock with `termux-wake-unlock`.

## 4. Get the phone's private Tailscale IP

In the Tailscale admin console, open **Machines / Devices**, select the Android phone, and copy its Tailscale IPv4 address (usually in the `100.x.y.z` range). Do not use the phone's public IP and do not port-forward port 3001 to the internet.

The private API base URL is:

```
http://100.x.y.z:3001/v1
```

Replace the sample address with the phone's actual Tailscale IP.

## 5. Allow GitHub Actions to join the private network

In the Tailscale admin console, create a pre-authentication key for the GitHub runner. Recommended settings:

- Reusable
- Ephemeral
- Tagged identity (for example `tag:ci`)
- Pre-approved, if device approval is enabled

If your tailnet uses custom access-control rules, allow `tag:ci` to reach the Android device on TCP port `3001`. Keep access limited to this port where possible.

In GitHub, open **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|---|---|
| `FREELLMAPI_BASE_URL` | `http://100.x.y.z:3001/v1` using the phone's actual Tailscale IP |
| `FREELLMAPI_API_KEY` | The unified `freellmapi-...` key from the dashboard |
| `FREELLMAPI_MODEL` | `auto` or the model/profile ID you tested in the dashboard |
| `TAILSCALE_AUTHKEY` | The ephemeral reusable Tailscale auth key |

Do not paste any of these keys into source files, issues, pull requests, or chat.

## 6. How the factory uses it

- MoneyPrinterTurbo script generation: FreeLLMAPI through its OpenAI-compatible endpoint.
- YouTube SEO metadata and narration draft: FreeLLMAPI first, Gemini fallback.
- Persian subtitle translation: OmniRoute first (when configured), then FreeLLMAPI, then Gemini.
- If the phone gateway is unavailable, the workflow's no-inference health check marks it unavailable; MoneyPrinterTurbo uses Gemini if its key is configured.
- The workflows use Tailscale only when both the FreeLLMAPI URL and Tailscale auth key are configured.

The gateway health check calls only `GET /v1/models`; it does not generate text or consume inference tokens.
