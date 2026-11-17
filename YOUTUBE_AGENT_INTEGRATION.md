# YouTube Agent toolkit integration

This repository vendors the MIT-licensed [Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) toolkit under `.claude/skills/yt-*`.

## Included capabilities

Eleven skills are included: `yt-script`, `yt-package`, `yt-edit`, `yt-comment`, `yt-plan`, `yt-viral`, `yt-retention`, `yt-shorts`, `yt-seo`, `yt-chapters`, and `yt-audit`. Their six dependency-free Python helpers and the upstream MIT license are included too.

## Factory integration and orchestration

The central `youtube-autonomous-manager` skill coordinates the toolkit with the existing MoneyPrinterTurbo, free-only model routing, competitor research, SEO validation, Persian subtitles, documentary assembly, YouTube publishing, and analytics components.

Run the manual GitHub Actions workflow **YouTube Agent orchestration hand-off** to validate the skill/tool map and produce an `youtube-agent-handoff` artifact containing:
- `execution-plan.json`: machine-readable mapping of all 11 skills to phases and existing factory tools.
- `agent-handoff.md`: constraints and instructions for a compatible agent session.

The dispatcher is deliberately plan-only. It does not call an LLM, execute SKILL.md instructions, render videos, upload, or publish. GitHub Actions does not interpret SKILL.md files by itself. Actual skill execution requires a compatible agent runtime/session that loads the manager and relevant skill files. No paid agent provider is enabled by this workflow.

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
- Never report a skill as executed unless an agent session/log proves it ran; never report publication without confirmed YouTube API upload IDs.
- Never expose API keys, OAuth tokens, or Tailscale credentials.
