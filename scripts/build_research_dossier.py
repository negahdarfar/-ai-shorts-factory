#!/usr/bin/env python3
"""Build a citation-checked factual research dossier from curated source notes.

This tool validates evidence structure; it does not fetch sources or independently
verify that source content is true. Human/editorial verification remains required.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


class ResearchError(ValueError):
    """Raised when the evidence dossier is incomplete or internally inconsistent."""


SOURCE_TYPES = {"primary", "academic", "news", "reference", "other"}
CLAIM_STATUSES = {"confirmed", "disputed", "unverified"}


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _date(value: object, field: str, required: bool = False) -> str | None:
    text = _clean(value)
    if not text:
        if required:
            raise ResearchError(f"Missing {field}.")
        return None
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ResearchError(f"{field} must use YYYY-MM-DD format.") from exc
    return text


def _domain(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ResearchError("Every source URL must be a valid HTTPS URL.")
    return parsed.hostname.lower().removeprefix("www.")


def build_research_dossier(input_path: str | Path, output_path: str | Path,
                           report_path: str | Path | None = None,
                           min_sources: int = 3, min_domains: int = 3) -> dict:
    try:
        raw = json.loads(Path(input_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchError(f"Cannot read research input: {exc}") from exc
    if not isinstance(raw, dict):
        raise ResearchError("Research input must be a JSON object.")

    topic = _clean(raw.get("topic"))
    if not topic:
        raise ResearchError("Research topic is required.")
    research_date = _date(raw.get("research_date"), "research_date", required=True)
    sources = raw.get("sources")
    claims = raw.get("claims")
    if not isinstance(sources, list) or len(sources) < min_sources:
        raise ResearchError(f"At least {min_sources} source records are required.")
    if not isinstance(claims, list) or not claims:
        raise ResearchError("At least one factual claim is required.")

    source_map: dict[str, dict] = {}
    domains: set[str] = set()
    clean_sources = []
    for index, item in enumerate(sources):
        if not isinstance(item, dict):
            raise ResearchError(f"Source {index + 1} must be an object.")
        sid = _clean(item.get("id"))
        title = _clean(item.get("title"))
        publisher = _clean(item.get("publisher"))
        url = _clean(item.get("url"))
        source_type = _clean(item.get("source_type")).lower()
        if not sid or sid in source_map:
            raise ResearchError(f"Source {index + 1} requires a unique non-empty id.")
        if not title or not publisher:
            raise ResearchError(f"Source {sid} requires title and publisher.")
        if source_type not in SOURCE_TYPES:
            raise ResearchError(f"Source {sid} has unsupported source_type.")
        domain = _domain(url)
        published_at = _date(item.get("published_at"), f"{sid}.published_at")
        accessed_at = _date(item.get("accessed_at"), f"{sid}.accessed_at", required=True)
        if published_at and date.fromisoformat(published_at) > date.fromisoformat(research_date):
            raise ResearchError(f"Source {sid} published_at cannot be after research_date.")
        if date.fromisoformat(accessed_at) > date.fromisoformat(research_date):
            raise ResearchError(f"Source {sid} accessed_at cannot be after research_date.")
        row = {
            "id": sid, "title": title, "publisher": publisher, "url": url,
            "domain": domain, "source_type": source_type,
            "published_at": published_at, "accessed_at": accessed_at,
        }
        source_map[sid] = row
        domains.add(domain)
        clean_sources.append(row)

    if len(domains) < min_domains:
        raise ResearchError(f"Sources must represent at least {min_domains} distinct domains.")

    clean_claims = []
    for index, item in enumerate(claims):
        if not isinstance(item, dict):
            raise ResearchError(f"Claim {index + 1} must be an object.")
        cid = _clean(item.get("id"))
        statement = _clean(item.get("claim"))
        status = _clean(item.get("status")).lower()
        notes = _clean(item.get("notes"))
        refs = item.get("source_ids")
        if not cid or not statement:
            raise ResearchError(f"Claim {index + 1} requires id and claim text.")
        if status not in CLAIM_STATUSES:
            raise ResearchError(f"Claim {cid} status must be confirmed, disputed, or unverified.")
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise ResearchError(f"Claim {cid} must cite one or more non-empty source_ids.")
        if len(set(refs)) != len(refs):
            raise ResearchError(f"Claim {cid} contains duplicate source references.")
        unknown = sorted(set(refs) - set(source_map))
        if unknown:
            raise ResearchError(f"Claim {cid} references unknown source ids: {', '.join(unknown)}.")
        cited_domains = {source_map[sid]["domain"] for sid in refs}
        if status == "confirmed" and len(cited_domains) < 2:
            raise ResearchError(f"Confirmed claim {cid} needs sources from at least two distinct domains.")
        if status == "disputed" and (len(cited_domains) < 2 or not notes):
            raise ResearchError(f"Disputed claim {cid} needs at least two domains and an explanation in notes.")
        clean_claims.append({
            "id": cid, "claim": statement, "status": status,
            "source_ids": refs, "source_domains": sorted(cited_domains), "notes": notes,
            "usable_in_narration": status == "confirmed",
        })

    if len({c["id"] for c in clean_claims}) != len(clean_claims):
        raise ResearchError("Claim ids must be unique.")
    unverified = [c["id"] for c in clean_claims if c["status"] == "unverified"]
    dossier = {
        "schema_version": 1,
        "topic": topic,
        "research_date": research_date,
        "source_count": len(clean_sources),
        "distinct_domain_count": len(domains),
        "sources": clean_sources,
        "claims": clean_claims,
        "unverified_claim_ids": unverified,
        "research_gate": "passed" if not unverified else "blocked",
        "editorial_note": "Only confirmed claims are marked usable_in_narration. Disputed and unverified claims must not be narrated as established facts.",
        "verification_limit": "This report validates citation structure and metadata only; it does not independently verify source accuracy, source independence, or rights to reuse source material.",
    }
    Path(output_path).write_text(json.dumps(dossier, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report_path:
        lines = [
            f"# Research dossier: {topic}", "",
            f"- Research date: {research_date}",
            f"- Sources: {len(clean_sources)} across {len(domains)} domains",
            f"- Research gate: {dossier['research_gate']}", "",
            "## Claims", "",
        ]
        for claim in clean_claims:
            lines.extend([
                f"### {claim['id']} — {claim['status'].upper()}",
                claim["claim"],
                f"Sources: {', '.join(claim['source_ids'])}",
            ])
            if claim["notes"]:
                lines.append(f"Editorial note: {claim['notes']}")
            lines.append("")
        lines.extend(["## Sources", ""])
        for source in clean_sources:
            lines.append(f"- [{source['id']}] {source['title']} — {source['publisher']} ({source['domain']}) — {source['url']}")
        lines.extend(["", "> " + dossier["verification_limit"], ""])
        Path(report_path).write_text("\n".join(lines), encoding="utf-8")
    return dossier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="longform-output/research-dossier.json")
    parser.add_argument("--report", default="longform-output/research-dossier.md")
    parser.add_argument("--min-sources", type=int, default=3)
    parser.add_argument("--min-domains", type=int, default=3)
    args = parser.parse_args()
    try:
        result = build_research_dossier(args.input, args.output, args.report, args.min_sources, args.min_domains)
    except ResearchError as exc:
        raise SystemExit(f"RESEARCH_QA_FAILED: {exc}") from exc
    print(f"RESEARCH_QA_{result['research_gate'].upper()}")
    if result["research_gate"] != "passed":
        raise SystemExit("Unverified claims block the research gate.")


if __name__ == "__main__":
    main()
