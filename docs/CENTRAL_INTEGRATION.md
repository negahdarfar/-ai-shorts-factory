# KOROUSH CENTRAL AI integration

This bridge is shared by the Short, Viral and Long video studios. It does not replace their renderers, media QA, subtitle pipeline, or YouTube uploader.

## Central contract
- Central repository: `negahdarfar/KOROUSH-CENTRAL-AI`.
- Built-in research route: `POST /api/integrations/youtube/research`.
- Discovery: `GET /api/platform/manifest` and `GET /api/integrations`.
- Registered connector IDs can be selected with `KOROUSH_CENTRAL_INTEGRATION_ID` after the central administrator activates a compatible `research.workflow.v1` connector for this exact repository.
- The bridge submits caller-supplied evidence to the central durable workflow (research brief → classification → synthesis → optional Persian translation), then polls the tenant-scoped job status.

The central workflow currently researches only the supplied evidence. It does not crawl websites, fetch source URLs, install external code, generate/render video, or publish to YouTube. New resources must be ingested and assessed by an approved collector before their evidence is sent. Central agent/model routing remains centrally governed; consumers do not pin or bypass providers.

## Required repository Actions secrets
- `KOROUSH_CENTRAL_BASE_URL`: HTTPS base URL of the deployed central service.
- `KOROUSH_CENTRAL_TENANT_KEY`: repository-bound tenant key; never put it in files or logs.

The central administrator must approve the exact repository identity, assign scopes `jobs:enqueue`, `jobs:read`, and `inference:chat`, and enable the durable worker, encrypted payload storage and a verified zero-cost eligible model. The central service must be deployed from a revision that actually contains the documented integration routes; a feature branch alone is not a production endpoint.

## Evidence contract
Supply a JSON array or `{"evidence":[...]}` with 1–8 unique source records. Each record requires `source_id` and `text` (max 5,000 characters); combined text is max 20,000 characters. Optional provenance fields: `publisher`, HTTPS `source_url`, timezone-aware `observed_at`. The bridge never dereferences URLs.

Example:
```json
[
  {
    "source_id": "trend-001",
    "publisher": "Approved source",
    "source_url": "https://example.org/article",
    "observed_at": "2026-11-25T04:00:00Z",
    "text": "A bounded excerpt collected and reviewed by this repository."
  }
]
```

Run:
```bash
python scripts/koroush_central_bridge.py --evidence-file evidence.json --idempotency-key "youtube-${GITHUB_RUN_ID}"
```

Set `KOROUSH_CENTRAL_INTEGRATION_ID=youtube` for the built-in YouTube profile, or use an active registered connector ID. Stable idempotency keys make retries safe. The bridge fails closed on unavailable/incompatible catalogs, invalid evidence, missing secrets, unsafe status URLs, failed jobs and timeouts.

## Activation boundary
The bridge code and offline tests do not prove production connectivity. Mark a studio connected only after its own tenant key is installed and a real authenticated job reaches `succeeded`. Public publishing remains governed by the studio's existing publishing safety controls and is not enabled by this bridge.
