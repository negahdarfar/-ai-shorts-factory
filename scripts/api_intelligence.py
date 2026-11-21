#!/usr/bin/env python3
"""Read-only API discovery from the public-apis catalogue.

No API credentials are read, no service is integrated automatically, and health
checks are opt-in. Health checks only send HEAD requests to public HTTPS hosts
listed in the upstream catalogue; redirects and private/local IP targets are blocked.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CATALOGUE_URL = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
USER_AGENT = "KoroushAPIIntelligence/1.0 (+read-only catalogue audit)"
PRIORITY_CATEGORIES = {
    "Cryptocurrency", "Blockchain", "Currency Exchange", "News",
    "Video", "Machine Learning", "Photography", "Social",
}
CATEGORY_WEIGHTS = {
    "Cryptocurrency": 10, "Blockchain": 10, "News": 9, "Video": 9,
    "Machine Learning": 9, "Photography": 8, "Social": 7, "Currency Exchange": 8,
}

def parse_catalogue(markdown: str) -> list[dict]:
    """Parse API rows from category tables in the upstream README."""
    category = ""
    entries = []
    for raw_line in markdown.splitlines():
        heading = re.match(r"^###\s+(.+?)\s*$", raw_line)
        if heading:
            category = heading.group(1).strip()
            continue
        line = raw_line.strip()
        if not category or not line.startswith("|") or line.startswith("|---") or line.startswith("|:"):
            continue
        cells = [part.strip() for part in line.strip("|").split("|")]
        if len(cells) < 5 or cells[0].lower() in {"api", "name"}:
            continue
        link = re.search(r"\[([^\]]+)\]\((https?://[^)]+)\)", cells[0])
        if not link:
            continue
        entries.append({
            "name": link.group(1).strip(), "url": link.group(2).strip(),
            "description": cells[1].strip(), "auth": cells[2].strip().strip(chr(96)),
            "https": cells[3].strip().lower(), "cors": cells[4].strip().lower(),
            "category": category,
        })
    return entries

def rank_entry(entry: dict) -> int:
    score = CATEGORY_WEIGHTS.get(entry["category"], 0)
    auth = entry["auth"].lower().replace(" ", "")
    if auth in {"no", "none"}:
        score += 4
    elif "apikey" in auth:
        score += 1
    if entry["https"] == "yes":
        score += 2
    if entry["cors"] == "yes":
        score += 1
    return score

def public_https_url(url: str) -> tuple[bool, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False, "HTTPS URL required"
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False, "local host blocked"
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
        if not addresses:
            return False, "DNS returned no addresses"
        if any(not ipaddress.ip_address(address).is_global for address in addresses):
            return False, "non-public IP blocked"
    except (OSError, ValueError) as exc:
        return False, f"DNS validation failed: {type(exc).__name__}"
    return True, "public HTTPS host"

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def check_url(url: str, timeout: int = 8) -> dict:
    allowed, reason = public_https_url(url)
    if not allowed:
        return {"status": "SKIPPED", "detail": reason}
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(request, timeout=timeout) as response:
            return {"status": str(response.status), "detail": "HEAD response"}
    except urllib.error.HTTPError as exc:
        return {"status": str(exc.code), "detail": "HTTP response; endpoint health not guaranteed"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": "ERROR", "detail": type(exc).__name__}

def load_catalogue() -> str:
    request = urllib.request.Request(CATALOGUE_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")

def render_markdown(records: list[dict], checked_at: str) -> str:
    lines = [
        "# KOROUSH API Intelligence — Discovery Report", "",
        f"- Generated (UTC): {checked_at}",
        f"- Candidate APIs: {len(records)}",
        "- Mode: read-only discovery; no API keys read; no service auto-integrated.", "",
        "| Score | Category | API | Auth | HTTPS | CORS | Check |",
        "|---:|---|---|---|---|---|---|",
    ]
    for item in records:
        check = item.get("health", {}).get("status", "NOT_CHECKED")
        name = item["name"].replace("|", "\\|")
        lines.append(f"| {item['score']} | {item['category']} | [{name}]({item['url']}) | {item['auth']} | {item['https']} | {item['cors']} | {check} |")
    lines += [
        "", "## Safety and interpretation", "",
        "- Catalogue labels are upstream claims, not proof of a free production quota.",
        "- A documentation URL returning HTTP 200 does not prove API endpoint health or commercial-use rights.",
        "- No authentication does not mean unlimited use. Confirm rate limits, terms, attribution, and licensing before adoption.",
        "- Health checks are optional HEAD requests to public HTTPS hosts only; redirects and private/local IPs are blocked.",
        "- Secrets are never read, printed, transmitted, or modified by this tool.", "",
        "Source: https://github.com/public-apis/public-apis",
    ]
    return "\n".join(lines) + "\n"

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="api-intelligence-report")
    parser.add_argument("--check", action="store_true", help="HEAD-check selected catalogue documentation URLs")
    parser.add_argument("--check-limit", type=int, default=12)
    args = parser.parse_args()
    parsed = parse_catalogue(load_catalogue())
    candidates = [item for item in parsed if item["category"] in PRIORITY_CATEGORIES and item["https"] == "yes"]
    for item in candidates:
        item["score"] = rank_entry(item)
    candidates.sort(key=lambda item: (-item["score"], item["category"], item["name"].casefold()))
    if args.check:
        selected = candidates[:max(0, min(args.check_limit, 30))]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            checks = list(pool.map(lambda item: check_url(item["url"]), selected))
        for item, result in zip(selected, checks):
            item["health"] = result
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": generated, "source": CATALOGUE_URL, "mode": "read_only",
        "parsed_catalogue_entries": len(parsed), "priority_candidates": len(candidates),
        "records": candidates,
    }
    (out / "api_candidates.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "API_INTELLIGENCE_REPORT.md").write_text(render_markdown(candidates, generated), encoding="utf-8")
    print(f"API_INTELLIGENCE_OK | parsed={len(parsed)} | candidates={len(candidates)} | output={out}")
    print("READ_ONLY=true | SECRETS_ACCESSED=0 | AUTO_INTEGRATION=0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
