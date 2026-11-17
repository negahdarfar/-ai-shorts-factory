# Persistent OmniRoute gateway for AI Shorts Factory

This deploys OmniRoute on an always-on VPS. GitHub Actions connects to it over HTTPS.
The gateway database and provider connections persist in a Docker volume.

## 1. VPS prerequisites

- Ubuntu 22.04+ (or another supported Linux server)
- Docker Engine and Docker Compose plugin
- A DNS hostname (for example `ai-gateway.example.com`) pointing to the VPS
- Inbound TCP ports 80 and 443 available for Caddy

Do not expose port 20128 directly to the public internet. Compose binds it to loopback only.

## 2. Start OmniRoute

On the VPS:

```bash
git clone https://github.com/negahdarfar/-ai-shorts-factory.git
cd ./-ai-shorts-factory/deploy/omniroute
cp .env.example .env
openssl rand -base64 48
openssl rand -hex 32
```

Put the first generated value in `JWT_SECRET`, the second in `API_KEY_SECRET`,
and set a long unique `INITIAL_PASSWORD` in `.env`. Do not commit or share this file.

Start the gateway:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f omniroute
```

## 3. Enable HTTPS

Install Caddy on the VPS, replace the hostname in `Caddyfile.example`, and install it
as Caddy's active configuration (usually `/etc/caddy/Caddyfile`). Then reload Caddy:

```bash
sudo systemctl reload caddy
```

The hostname must resolve to the VPS and ports 80/443 must be reachable. The public
base URL used by GitHub must end in `/v1`, for example:

```
https://ai-gateway.example.com/v1
```

## 4. Connect provider accounts

Open the HTTPS hostname in a browser and sign in with `INITIAL_PASSWORD`.

1. Open **Providers** and connect the provider accounts/API keys you are entitled to use.
2. For free-tier routing, connect eligible free-tier accounts and create a free-only
   Combo in **Combos**. Do not include paid providers in that Combo if you want to
   prevent paid fallback.
3. Open **Endpoints** and create an API key with the `chat` scope.
4. Copy the generated endpoint key securely. Do not put provider credentials or this
   key in source code.

OmniRoute is a gateway, not a grant of free inference. Provider free-tier eligibility,
quotas, rate limits, and terms are controlled by each upstream provider. The `auto`
model can use any eligible route configured in the gateway; use a free-only Combo/model
when you need to restrict routing to free providers.

## 5. Configure GitHub Actions

In the GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**
and add:

| Secret | Value |
|---|---|
| `OMNIROUTE_BASE_URL` | HTTPS gateway URL ending in `/v1` |
| `OMNIROUTE_API_KEY` | Endpoint key created in OmniRoute |
| `OMNIROUTE_MODEL` | `auto` or the exact free-only Combo/model ID |

Keep `GEMINI_API_KEY` configured as a fallback until OmniRoute is tested. The recovery
workflow tries OmniRoute first and falls back to Gemini if the gateway fails.

Then run **Actions → OmniRoute Gateway Check → Run workflow**. This checks the HTTPS
health endpoint and model catalogue without generating text or consuming inference tokens.

## 6. Security and operations

- Keep `.env` private; it contains server secrets.
- Keep port 20128 bound to loopback; use HTTPS through Caddy.
- Back up the Docker volume `omniroute_data` and keep the encryption/auth secrets safe.
- Update OmniRoute deliberately: review the release, then rebuild with
  `docker compose build --pull && docker compose up -d`.
- Never paste provider API keys into issues, pull requests, workflow logs, or chat.

## GitHub-hosted runner mode

The subtitle workflow also supports a remote OmniRoute endpoint through the three
repository secrets above. GitHub-hosted runners are temporary; they cannot provide a
persistent OmniRoute database or provider-account session between jobs. The VPS is the
persistent server, while GitHub Actions is the client/automation runner.
