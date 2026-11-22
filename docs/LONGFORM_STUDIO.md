# Longform Studio

This branch contains a manual render-and-QA path for long-form documentary videos.

## Inputs

1. Commit source clips to the repository and create a UTF-8 JSON manifest, for example:

```json
[
  "assets/longform/scene-01.mp4",
  "assets/longform/scene-02.mp4",
  "assets/longform/scene-03.mp4"
]
```

Paths are resolved from the repository root. Every clip must exist inside the checkout.

Create a rights ledger (default: `data/longform/rights.json`) with one object per clip. Example:

```json
[
  {
    "asset": "assets/longform/scene-01.mp4",
    "source_url": "https://example.org/original-source",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": "Creator name — source title"
  },
  {
    "asset": "assets/longform/scene-02.mp4",
    "source_url": "https://example.org/owned-footage-record",
    "license": "owned",
    "license_url": "https://example.org/rights-document",
    "attribution": "Original footage produced by our team",
    "rights_holder": "Rights holder name"
  }
]
```

Accepted license families: Public Domain/CC0, CC BY, CC BY-SA (requires `share_alike_acknowledged: true`), and footage marked `owned` with a named `rights_holder`. NC, ND, unknown, or incomplete records fail closed. Each record must include HTTPS source and license/evidence URLs plus attribution. A passing ledger checks metadata completeness; it does not independently prove that a claim is true or that the source actually grants the stated rights.

Optional inputs:
- Persian UTF-8 SRT file, for example `assets/longform/subtitles.fa.srt`
- Narration audio, for example `assets/longform/narration.wav`
- Burn subtitles: enabled only when an SRT path is supplied

## Mixed-media storyboard rendering

The render workflow now accepts a storyboard manifest containing still images, short video clips, or both. Existing string-only video manifests remain supported. New object entries use repository-relative paths:

```json
[
  {"path": "assets/longform/establishing.jpg", "type": "image", "duration": 8, "motion": "zoom_in"},
  {"path": "assets/longform/archive-short.mp4", "type": "video", "start": 3, "end": 17},
  {"path": "assets/longform/map.png", "type": "image", "duration": 10, "motion": "pan_right"},
  {"path": "assets/longform/interview.mp4", "type": "video", "start": 12, "end": 28}
]
```

Image scenes support `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, and `static`; their default duration is 6 seconds and allowed range is 1–120 seconds. Video scenes can be trimmed with `start` and `end` seconds. Every scene is normalized to 1920×1080, 30 fps H.264, then joined in storyboard order. The renderer creates a silent audio track when no narration is supplied so the technical output has an audio stream; this is not a substitute for a finished soundtrack. A supplied Persian SRT can be burned into the final render.

The rights ledger remains mandatory for every distinct media file, whether it is a photograph or a video. Reusing a source file in multiple timeline scenes does not require duplicate rights records. This stage does not fetch media automatically, create AI images, generate narration, or establish copyright ownership; those are separate pipeline stages and must retain provenance and license checks.

## Free AI script generation and Commons media acquisition

The workflow has an optional `auto_generate_plan` switch. When enabled, it asks only models explicitly identified as free by the configured FreeLLMAPI or OpenRouter model catalogue to draft an English documentary script and chapter-by-chapter visual plan. It requires at least three claims already marked `confirmed` in the curated research dossier, each backed by source URLs on at least two HTTPS hostnames. Disputed and unverified claims are excluded from the prompt. The output is labelled `AI_DRAFT_REQUIRES_SOURCE_AND_EDITORIAL_REVIEW`; this is not an automatic fact-check and is not cleared for public publishing.

Required GitHub Actions secrets for AI generation:
- `FREELLMAPI_BASE_URL` and `FREELLMAPI_API_KEY` for the self-hosted FreeLLMAPI gateway
- Optional `FREELLMAPI_MODEL` preference
- Optional `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` as fallback

The free-model router rejects unknown-price models instead of assuming they are free. If no explicitly free model is available, the workflow stops with a clear error rather than silently using a paid model. API keys are read from GitHub Secrets and are never written into generated artifacts.

When an AI or manually supplied storyboard plan is available, the workflow searches Wikimedia Commons for each visual query and downloads eligible images or short video clips. It automatically accepts only Public Domain, CC0, and CC BY metadata; it deliberately excludes CC BY-SA, NC, ND, and unclear licenses until a separate compatibility review is made. It records the Commons file page, license URL, creator attribution, and downloaded asset path in a generated rights ledger. It prefers the requested media type and falls back from a missing video to a still image. Video clips are capped at 15 seconds by default and require FFprobe to report a usable duration.

The downloader is bounded to 8 Commons results per scene and 80 MB per downloaded asset. It does not bypass paywalls, scrape commercial streaming platforms, or download YouTube/movie/TV clips. Commons metadata can be incomplete or incorrect: inspect each original file page and attribution before commercial use. A successful rights metadata gate is not legal advice or proof of ownership. If some scenes have no eligible media, the report lists them; the final minimum-duration gate can still fail if too little footage was found.

To run the automated path, open **Actions → Koroush Longform Studio - render and QA → Run workflow**, enable `auto_generate_plan`, and provide a curated research dossier containing enough confirmed claims. Set `minimum_duration_seconds` to the desired target runtime (for example 480 for eight minutes). Ensure the AI provider secrets above are configured. The manual `storyboard_plan` input can be used instead when a plan already exists.

## Candidate source discovery

The workflow can collect candidate links from configurable RSS/Atom feeds using Python's standard library and also queues every HTTPS URL already listed in the curated research dossier. Configure data/longform/research_feeds.json with trusted publisher feed URLs. Curated source URLs are included even when the feed list is empty, so the evidence audit can inspect the actual cited sources rather than only newly discovered RSS links. The collector filters titles/descriptions against the documentary topic, deduplicates links, and applies HTTPS, timeout, and response-size limits. Its research-candidates.json output is included in the workflow artifact.

Candidates are discovery leads only: the collector does not download full articles, infer facts, create claims, or mark sources confirmed. A human/editorial research step must read the linked material and curate the evidence in research.json. An empty feed list is allowed and produces zero candidates; replace the empty list with real official RSS/Atom feed URLs to activate discovery.

## Research page extraction

After RSS discovery, the workflow now attempts to fetch up to 20 candidate pages and extract bounded readable HTML text into `longform-output/research-extracts.json`. It accepts HTTPS HTML pages only, blocks non-public IP destinations and unsafe redirects, limits each response to 1.5 MB, and records individual failures without losing other candidates. Script/style/navigation/footer content is excluded where identifiable. JavaScript-rendered pages, PDFs, paywalls, and pages requiring login are not handled. Extraction is not fact-checking: the output is unverified material for editorial review, and the separate curated `research.json` dossier remains the only research-gate input.

## Research evidence audit

After the dossier is validated, the workflow runs `scripts/audit_research_evidence.py` against the curated dossier and extracted page text. It links dossier sources to extracted pages by normalized exact HTTPS URL, then searches claim wording for lexical overlaps and records short matching excerpts in `research-evidence-audit.json` and `research-evidence-audit.md`. Sources that were not extracted or failed extraction are reported separately.

This is an evidence locator, not an automated fact-checker. Keyword overlap can miss paraphrases and can also produce misleading matches when context differs. It does not assess whether a source truly supports a claim, detect contradictions reliably, verify dates or numbers, change claim status, or promote any claim to confirmed. Editors must inspect the cited source and surrounding context. The curated dossier remains unchanged and remains the only research-gate input.

## Factual research input

The render workflow now requires `data/longform/research.json` (or another repository path supplied at dispatch). It is a curated evidence file, not a search engine. Use this structure:

```json
{
  "topic": "A documentary topic",
  "research_date": "2026-11-22",
  "sources": [
    {
      "id": "S1",
      "title": "Original research paper",
      "publisher": "Research institution",
      "url": "https://example.org/paper",
      "source_type": "academic",
      "published_at": "2025-06-01",
      "accessed_at": "2026-11-20"
    },
    {
      "id": "S2",
      "title": "Official data release",
      "publisher": "Public agency",
      "url": "https://agency.example.org/data",
      "source_type": "primary",
      "published_at": "2025-07-01",
      "accessed_at": "2026-11-20"
    },
    {
      "id": "S3",
      "title": "Independent review",
      "publisher": "Journal",
      "url": "https://journal.example.org/review",
      "source_type": "academic",
      "published_at": "2025-08-01",
      "accessed_at": "2026-11-21"
    }
  ],
  "claims": [
    {
      "id": "C1",
      "claim": "A concise factual statement supported by the sources.",
      "status": "confirmed",
      "source_ids": ["S1", "S2"]
    }
  ]
}
```

The validator requires at least three source records from three distinct host domains. Every claim must cite known source IDs. A claim marked `confirmed` needs sources from at least two domains; a `disputed` claim needs two domains and an editorial explanation. `unverified` claims block the research gate and are never marked usable in narration. The generated JSON and Markdown dossier are attached to the render artifact.

Important: this is a citation-structure and metadata check, not automatic fact-checking. It does not download/read the linked pages, prove that sources are independent, or determine whether a claim is true. Research sources must be read and curated by a human or a separately configured research agent. The workflow will not infer facts from titles or snippets.

## Run

Open **Actions → Koroush Longform Studio - render and QA → Run workflow** on the `longform-studio` branch. Supply the manifest path and optional assets. The default minimum duration is 480 seconds (8 minutes).

The workflow:
1. Validates that all inputs exist and remain inside the repository checkout.
2. Requires an exact rights-ledger record for every clip and rejects unclear/restricted licenses.
3. Normalizes clips to 1920×1080, 30 fps, H.264/AAC and joins them in manifest order.
4. Optionally replaces the clip audio with narration and burns the Persian subtitles into the video.
5. Requires a 16:9 output, at least 1280×720, an audio stream, and the configured minimum duration.
6. Uploads the MP4 and JSON QA report as a 14-day Actions artifact.

## Important limitations

- This workflow validates a supplied, curated research dossier and assembles supplied footage; it discovers candidate links from configured RSS/Atom feeds and extracts bounded text from accessible HTML pages, but does not independently fact-check claims, generate a verified factual script, synthesize narration, or acquire licensed footage automatically.
- No YouTube upload or public publishing is performed by this workflow.
- A passed technical QA or rights-metadata report is not legal advice, proof of ownership, factuality review, editorial review, or a guarantee of audience retention.
- GitHub-hosted runners have time, storage, and artifact limits. Large footage collections may exceed those limits.
