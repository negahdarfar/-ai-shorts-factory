#!/usr/bin/env python3
"""Discover free academic and encyclopedia source candidates for a documentary topic."""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "KoroushLongformStudio/1.0 (topic research discovery)"


def fetch_json(url: str, timeout: int = 20) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Discovery API returned a non-object response.")
    return payload


def secure_url(value):
    parsed = urllib.parse.urlparse(str(value or ""))
    if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
        return parsed.geturl()
    return ""


def openalex_candidates(topic, limit=10):
    params = urllib.parse.urlencode({
        "search": topic, "per-page": str(limit),
        "select": "id,doi,title,publication_year,primary_location,authorships,open_access",
    })
    data = fetch_json("https://api.openalex.org/works?" + params)
    rows = []
    for item in data.get("results", []):
        location = item.get("primary_location") or {}
        url = secure_url(location.get("landing_page_url")) or secure_url(item.get("doi"))
        if not url:
            continue
        authors = item.get("authorships") or []
        first_author = ((authors[0].get("author") or {}).get("display_name") if authors else "") or ""
        rows.append({
            "source_id": "OA-" + str(item.get("id", "")).rsplit("/", 1)[-1],
            "title": str(item.get("title") or "Untitled scholarly work")[:500],
            "url": url,
            "publisher": str((location.get("source") or {}).get("display_name") or "OpenAlex indexed publisher"),
            "published_at": str(item.get("publication_year") or ""),
            "source_type": "scholarly",
            "creator": first_author,
            "discovery_provider": "OpenAlex",
            "discovery_only": True,
            "editorial_status": "candidate_requires_full_text_review",
        })
    return rows


def crossref_candidates(topic, limit=10):
    params = urllib.parse.urlencode({
        "query.bibliographic": topic, "rows": str(limit),
        "select": "DOI,title,publisher,published,URL,type,author",
    })
    data = fetch_json("https://api.crossref.org/works?" + params)
    rows = []
    for item in data.get("message", {}).get("items", []):
        url = secure_url(item.get("URL"))
        if not url:
            continue
        title = (item.get("title") or ["Untitled scholarly work"])[0]
        published_meta = item.get("published") or item.get("published-print") or item.get("published-online") or {}
        published = published_meta.get("date-parts", [[None]])[0]
        year = str(published[0]) if published and published[0] else ""
        authors = item.get("author") or []
        creator = " ".join(str(authors[0].get(k, "")) for k in ("given", "family")).strip() if authors else ""
        rows.append({
            "source_id": "CR-" + str(item.get("DOI", "")).replace("/", "_"),
            "title": str(title)[:500],
            "url": url,
            "publisher": str(item.get("publisher") or "Crossref registered publisher"),
            "published_at": year,
            "source_type": "scholarly",
            "creator": creator,
            "discovery_provider": "Crossref",
            "discovery_only": True,
            "editorial_status": "candidate_requires_full_text_review",
        })
    return rows


def wikipedia_candidates(topic, limit=5):
    params = urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": topic,
        "srnamespace": "0", "srlimit": str(limit), "format": "json",
    })
    data = fetch_json("https://en.wikipedia.org/w/api.php?" + params)
    rows = []
    for item in data.get("query", {}).get("search", []):
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="()_")
        rows.append({
            "source_id": "WP-" + str(item.get("pageid", "")),
            "title": title,
            "url": url,
            "publisher": "Wikipedia",
            "published_at": "",
            "source_type": "encyclopedia_lead",
            "discovery_provider": "Wikipedia",
            "discovery_only": True,
            "editorial_status": "lead_only_not_sufficient_as_factual_evidence",
        })
    return rows


def discover(topic, output, limit=10):
    if not topic.strip():
        raise ValueError("A documentary topic is required.")
    errors, combined, seen = [], [], set()
    for provider, function in (
        ("OpenAlex", openalex_candidates),
        ("Crossref", crossref_candidates),
        ("Wikipedia", wikipedia_candidates),
    ):
        try:
            rows = function(topic, limit)
            for row in rows:
                url = row["url"]
                if url not in seen:
                    seen.add(url)
                    combined.append(row)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({"provider": provider, "error": f"{type(exc).__name__}: {str(exc)[:300]}"})
    result = {
        "schema_version": 1,
        "topic": topic,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(combined),
        "candidates": combined,
        "provider_errors": errors,
        "warning": "These are discovery leads. Search ranking and metadata do not establish source quality, factual support, independence, or reuse rights.",
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output", default="longform-output/topic-candidates.json")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.limit <= 20:
        raise SystemExit("Limit must be 1-20.")
    try:
        result = discover(args.topic, args.output, args.limit)
    except Exception as exc:
        raise SystemExit(f"TOPIC_DISCOVERY_FAILED: {exc}") from exc
    print(f"TOPIC_DISCOVERY_READY candidates={result['candidate_count']} provider_errors={len(result['provider_errors'])}")


if __name__ == "__main__":
    main()
