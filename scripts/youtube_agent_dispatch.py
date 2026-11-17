#!/usr/bin/env python3
"""Build a verifiable execution contract for the vendored YouTube Agent skills.

This does not execute an LLM agent or publish videos. It prepares a plan and
agent hand-off prompt while validating that the referenced skills/tools exist.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "yt-plan": {"phase": "planning", "tools": ["scripts/build_trending_batch.py"]},
    "yt-viral": {"phase": "research", "tools": ["scripts/research_youtube_competitors.py"]},
    "yt-script": {"phase": "creative", "tools": ["scripts/generate_seo_metadata.py"]},
    "yt-package": {"phase": "packaging", "tools": ["scripts/generate_seo_metadata.py", "scripts/render_seo_thumbnails.py"]},
    "yt-seo": {"phase": "packaging", "tools": ["scripts/validate_seo_metadata.py"]},
    "yt-edit": {"phase": "postproduction", "tools": ["scripts/assemble_documentary.py"]},
    "yt-chapters": {"phase": "postproduction", "tools": ["scripts/validate_chapters.py"]},
    "yt-shorts": {"phase": "repurposing", "tools": ["scripts/assemble_documentary.py"]},
    "yt-retention": {"phase": "learning", "tools": ["scripts/youtube_analytics_report.py", ".claude/skills/yt-retention/retention.py"]},
    "yt-comment": {"phase": "community", "tools": []},
    "yt-audit": {"phase": "learning", "tools": ["scripts/youtube_analytics_report.py"]},
}
PIPELINE_GATES = [
    "Four distinct topics; no recent duplicates.",
    "Use real competitor metrics only when YouTube API data is available.",
    "English narration; Persian subtitles.",
    "Validate metadata, rendered media, subtitles, and visual uniqueness.",
    "Use free providers only; never assume unknown pricing is free.",
    "Do not upload publicly unless the existing approved scheduled-release path authorizes it.",
    "Confirm YouTube API upload IDs before reporting publication; avoid duplicate retries.",
]
def build_plan():
    entries = []
    missing = []
    for name, spec in SKILLS.items():
        skill_path = ROOT / ".claude" / "skills" / name / "SKILL.md"
        tools = []
        if not skill_path.is_file():
            missing.append(str(skill_path.relative_to(ROOT)))
        for item in spec["tools"]:
            exists = (ROOT / item).is_file()
            tools.append({"path": item, "exists": exists})
            if not exists:
                missing.append(item)
        entries.append({
            "skill": name,
            "skill_file": str(skill_path.relative_to(ROOT)),
            "skill_file_exists": skill_path.is_file(),
            "phase": spec["phase"],
            "tools": tools,
            "execution": "agent_required",
        })
    return {
        "schema_version": 1,
        "project": "ViralNovaLabs",
        "mode": "handoff_plan_only",
        "agent_runtime_executed": False,
        "publishing_performed": False,
        "skills_total": len(entries),
        "skills": entries,
        "pipeline_gates": PIPELINE_GATES,
        "missing_paths": sorted(set(missing)),
        "next_step": "Load .claude/skills/youtube-autonomous-manager/SKILL.md in a compatible agent session and execute only approved stages.",
    }

def render_prompt(plan):
    names = ", ".join(item["skill"] for item in plan["skills"])
    return f"""# ViralNovaLabs YouTube Agent hand-off

Load `.claude/skills/youtube-autonomous-manager/SKILL.md` and the relevant
project-local skill instructions before acting.

Available skills: {names}

This artifact is a hand-off contract, not proof that an agent ran. Execute the
pipeline in the manager's order. Use existing factory scripts as the execution
source of truth; do not create a parallel renderer/uploader.

## Mandatory constraints
{chr(10).join("- " + gate for gate in plan["pipeline_gates"])}

## Required report
Report which skills were actually loaded and used, commands run, output files
validated, upload IDs/URLs confirmed by YouTube, schedule times/timezone, and
all missing credentials or blocked stages. Never claim publication without
YouTube API confirmation. Do not expose secrets.
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="youtube-agent-plan")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    plan = build_plan()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "execution-plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "agent-handoff.md").write_text(render_prompt(plan), encoding="utf-8")
    print(f"Validated {plan['skills_total']} skills; missing paths: {len(plan['missing_paths'])}.")
    print("Plan mode only: no LLM invocation, upload, or publication was performed.")
    if args.check and plan["missing_paths"]:
        raise SystemExit("Required skill/tool paths are missing: " + ", ".join(plan["missing_paths"]))

if __name__ == "__main__":
    main()
