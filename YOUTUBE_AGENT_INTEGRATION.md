# YouTube Agent toolkit integration

This repository vendors the MIT-licensed [Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) toolkit under `.claude/skills/yt-*`.

## Included capabilities

Eleven skills are included: `yt-script`, `yt-package`, `yt-edit`, `yt-comment`, `yt-plan`, `yt-viral`, `yt-retention`, `yt-shorts`, `yt-seo`, `yt-chapters`, and `yt-audit`. Their six dependency-free Python helpers and the upstream MIT license are included too.

## Agent runtime

The manual **YouTube Agent free-model runtime** workflow now runs one selected skill using an OpenAI-compatible FreeLLMAPI endpoint:
- It reads the selected vendored `SKILL.md`, the project voice profile, and a repository JSON context file.
- It uses `scripts/free_model_router.py` to discover models and permits only IDs explicitly marked free (`:free`, `/free`, `-free`, or `_free`). Unknown-price models are rejected.
- It tries a bounded number of free models and writes a Markdown editorial artifact plus JSON execution metadata.
- It never invokes shell tools, renders media, uploads videos, publishes, or posts comments.

Required GitHub Actions secrets: either `FREELLMAPI_CLOUD_BASE_URL` + `FREELLMAPI_CLOUD_API_KEY`, or `FREELLMAPI_BASE_URL` + `FREELLMAPI_API_KEY`. The endpoint must expose OpenAI-compatible `GET /models` and `POST /chat/completions`. Do not paste secrets into chat or commit them. If no explicitly free model is advertised, the runtime fails closed.

To run it: Actions → **YouTube Agent free-model runtime** → Run workflow → select one skill, an existing JSON context file (default `data/previous_four_topics.json`), and a model-ranking task. Download the `youtube-agent-editorial-output` artifact after a successful run.

The separate **YouTube Agent orchestration hand-off** workflow remains a no-inference validation and plan artifact. GitHub Actions does not interpret SKILL.md by itself; the new runtime is the explicit model invocation layer for editorial drafts.

## Pipeline mapping

| Stage | Skill | Existing factory component |
|---|---|---|
| Planning | `yt-plan` | `scripts/build_trending_batch.py` |
| Research | `yt-viral` | `scripts/research_youtube_competitors.py` |
| Creative | `yt-script` | existing script generation in MoneyPrinterTurbo/documentary workflow |
| Packaging | `yt-package`, `yt-seo` | SEO metadata and thumbnail renderer/validator |
| Postproduction | `yt-edit`, `yt-chapters` | documentary assembly and chapter validation |
| Repurposing | `yt-shorts` | existing video assembly/editor |
| Community | `yt-comment` | draft replies only; no automatic comment posting |
| Learning | `yt-retention`, `yt-audit` | real YouTube analytics exports/reports |

## Safety and source of truth

- Preserve the existing scheduled production and release workflow; do not create a parallel scheduled generator.
- Prefer explicitly free providers. Unknown pricing is not free; no paid provider is silently enabled.
- Use real competitor and channel analytics only. State when data is unavailable.
- Validate scripts, metadata, rendered media, subtitles, and visual uniqueness before release.
- Public publishing remains governed by the existing scheduled-release path and its approval/QA gates.
- Never report a skill as executed unless the runtime log proves it ran; never report publication without confirmed YouTube API upload IDs.
- Never expose API keys, OAuth tokens, or Tailscale credentials.
