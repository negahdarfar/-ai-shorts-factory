#!/usr/bin/env python3
"""Discover relevant public GitHub repositories; read-only, no token required.

Uses GitHub's unauthenticated repository search API with conservative request
limits. Results are candidates for human review, never auto-installed or executed.
"""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com/search/repositories"
UA = "KoroushOpenSourceScout/1.0"
SEARCHES = {
    "llm": '("llm" OR "large language model") (in:name,description) language:Python',
    "video": '("text to video" OR "video generation" OR "video editor") (in:name,description) language:Python',
    "image_audio": '("image generation" OR "text to speech" OR "voice cloning") (in:name,description) language:Python',
    "automation": '("youtube automation" OR "content automation" OR "workflow automation") (in:name,description) language:Python',
}
MAX_RESULTS_PER_QUERY = 20


def fetch_repositories(query: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "q": query, "sort": "stars", "order": "desc",
        "per_page": MAX_RESULTS_PER_QUERY,
    })
    request = urllib.request.Request(
        API + "?" + params,
        headers={"Accept": "application/vnd.github+json", "User-Agent": UA,
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("items", [])


def normalize(repo: dict, category: str) -> dict:
    return {
        "name": repo.get("full_name", ""),
        "url": repo.get("html_url", ""),
        "description": repo.get("description") or "",
        "stars": repo.get("stargazers_count", 0),
        "language": repo.get("language") or "",
        "license": (repo.get("license") or {}).get("spdx_id", "UNKNOWN"),
        "archived": bool(repo.get("archived")),
        "fork": bool(repo.get("fork")),
        "updated_at": repo.get("updated_at", ""),
        "pushed_at": repo.get("pushed_at", ""),
        "topics": repo.get("topics", []),
        "category": category,
    }


def score(item: dict) -> int:
    points = min(int(item["stars"] or 0) // 1000, 30)
    if item["license"] not in {"UNKNOWN", "NOASSERTION"}:
        points += 8
    if item["pushed_at"]:
        points += 5
    if item["archived"]:
        points -= 40
    if item["fork"]:
        points -= 5
    return points


def main() -> int:
    parser_output = Path("api-intelligence-report")
    parser_output.mkdir(parents=True, exist_ok=True)
    found = {}
    errors = []
    for category, query in SEARCHES.items():
        try:
            for raw in fetch_repositories(query):
                item = normalize(raw, category)
                if item["name"]:
                    found[item["name"].lower()] = item
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
            errors.append({"category": category, "error": type(exc).__name__})
        time.sleep(1)
    results = list(found.values())
    for item in results:
        item["score"] = score(item)
    results.sort(key=lambda item: (-item["score"], -item["stars"], item["name"].casefold()))
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "generated_at_utc": generated,
        "source": "GitHub Repository Search API (unauthenticated)",
        "mode": "read_only_candidates",
        "results_count": len(results),
        "errors": errors,
        "results": results,
    }
    (parser_output / "github_project_candidates.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# KOROUSH Open-Source Project Scout", "",
        f"- Generated (UTC): {generated}",
        f"- Unique repositories: {len(results)}",
        "- Search mode: unauthenticated, read-only; no repositories cloned, installed, or executed.",
        "",
        "| Score | Category | Repository | Stars | License | Last push |",
        "|---:|---|---|---:|---|---|",
    ]
    for item in results:
        name = item["name"].replace("|", "\\|")
        lines.append(
            f"| {item['score']} | {item['category']} | [{name}]({item['url']}) | "
            f"{item['stars']} | {item['license']} | {item['pushed_at'][:10]} |"
        )
    lines += [
        "", "## Review checklist", "",
        "- Inspect source code, dependencies, security posture, license, and maintenance before adoption.",
        "- Stars and recent activity are discovery signals, not quality or safety guarantees.",
        "- GitHub's unauthenticated search quota is limited; rerun later if rate-limited.",
        "- No GitHub token or repository secrets are read or sent.",
    ]
    if errors:
        lines += ["", "## Search warnings", ""] + [
            f"- {entry['category']}: {entry['error']}" for entry in errors
        ]
    (parser_output / "GITHUB_PROJECT_SCOUT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"PROJECT_SCOUT_OK | unique_repositories={len(results)} | warnings={len(errors)}")
    print("READ_ONLY=true | REPOSITORIES_CLONED=0 | CODE_EXECUTED=0 | SECRETS_ACCESSED=0")
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
