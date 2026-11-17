# YouTube Agent toolkit integration

This repository vendors the MIT-licensed [Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) toolkit under `.claude/skills/yt-*`.

## Included capabilities

Eleven skills are included: `yt-script`, `yt-package`, `yt-edit`, `yt-comment`, `yt-plan`, `yt-viral`, `yt-retention`, `yt-shorts`, `yt-seo`, `yt-chapters`, and `yt-audit`. Their six dependency-free Python helpers and `.claude/youtube/voice.md` are included too. The upstream MIT license is retained at `.claude/skills/YOUTUBE-AGENT-LICENSE`.

## Factory integration

The central `youtube-autonomous-manager` skill coordinates these tools with the existing MoneyPrinterTurbo, FreeLLMAPI/free-only model routing, competitor research, SEO validation, Persian subtitle, documentary assembly, YouTube publishing, and analytics components. Read `.claude/skills/youtube-autonomous-manager/SKILL.md` for the operational map and safety gates.

| Stage | Toolkit | Existing factory component |
|---|---|---|
| Topic/competitor research | `yt-viral` | `scripts/research_youtube_competitors.py` |
| Hooks and script | `yt-script` | existing AI script generation in MoneyPrinterTurbo / documentary workflow |
| Title + thumbnail pairing | `yt-package` | `scripts/generate_seo_metadata.py`, `scripts/render_seo_thumbnails.py` |
| SEO | `yt-seo` | `scripts/validate_seo_metadata.py` and uploader metadata |
| Transcript edit list | `yt-edit` | FFmpeg/editor pipeline; the skill itself only proposes edits |
| Chapters | `yt-chapters` | description metadata and long-form documentary transcript |
| Long-to-Shorts ideas | `yt-shorts` | existing video assembly/editor; the skill proposes segments, it does not render cuts |
| Retention | `yt-retention` | YouTube Analytics exports |
| Comments | `yt-comment` | draft replies; no automatic comment posting is enabled by this toolkit |
| Planning | `yt-plan` | existing scheduled production calendar |
| Channel audit | `yt-audit` | channel analytics and packaging review |

## Use

Claude Code/compatible coding agents can load the project-local skills from `.claude/skills/`. The helper scripts require Python 3 and no third-party Python packages. Preserve the directory layout: several scripts import sibling helpers or read adjacent data files.

GitHub Actions does **not** interpret `SKILL.md` files as agent instructions by itself. The added CI workflow checks Python syntax only; actual skill execution requires an agent session that loads the skill. The existing scheduled production workflow remains the production/publishing engine.

## Quality and safety

- Preserve the free-only provider guard. No paid model is selected by this integration.
- The toolkit drafts and analyzes; it does not independently upload or publish.
- Use only actual channel analytics and collected competitor data.
- Review factual claims, source notes, edits, metadata, and thumbnail concepts before release.
- Do not automatically post comments or rewrite metadata on already-public videos.
