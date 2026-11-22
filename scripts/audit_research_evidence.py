#!/usr/bin/env python3
"""Audit curated research claims against extracted page text.

This is a lexical evidence locator, not an automated fact checker. It never
changes claim status or promotes a claim to confirmed.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, urlunparse


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
    "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their",
    "this", "to", "was", "were", "with", "و", "در", "به", "از", "که", "را",
    "این", "آن", "برای", "بر", "است", "بود", "شد", "می", "یک",
}


class EvidenceAuditError(ValueError):
    pass


def normalize_url(value: str) -> str:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return ""
    host = parsed.hostname.lower().removeprefix("www.")
    path = re.sub(r"/+$", "", parsed.path or "")
    return urlunparse(("https", host, path, "", parsed.query, ""))


def tokens(value: str) -> list[str]:
    words = re.findall(r"[^\W_]{2,}", str(value or "").lower(), flags=re.UNICODE)
    return [word for word in words if word not in STOPWORDS and not word.isdigit()]


def excerpts_for(text: str, terms: list[str], limit: int = 3) -> list[dict]:
    sentences = re.split(r"(?<=[.!?؟])\s+|\n+", text or "")
    scored = []
    for sentence in sentences:
        clean = re.sub(r"\s+", " ", sentence).strip()
        if len(clean) < 35:
            continue
        present = sorted({term for term in terms if term in clean.lower()})
        if present:
            scored.append((len(present), clean[:700], present))
    scored.sort(key=lambda row: (-row[0], len(row[1])))
    unique = []
    seen = set()
    for score, sentence, present in scored:
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append({"match_count": score, "matched_terms": present, "excerpt": sentence})
        if len(unique) >= limit:
            break
    return unique


def audit_research_evidence(dossier_path: str | Path, extracts_path: str | Path,
                            json_output: str | Path, markdown_output: str | Path) -> dict:
    try:
        dossier = json.loads(Path(dossier_path).read_text(encoding="utf-8"))
        extracts = json.loads(Path(extracts_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceAuditError(f"Cannot read audit input: {exc}") from exc
    if not isinstance(dossier, dict) or not isinstance(dossier.get("claims"), list):
        raise EvidenceAuditError("Dossier must be an object with a claims array.")
    if not isinstance(dossier.get("sources"), list):
        raise EvidenceAuditError("Dossier must contain a sources array.")
    pages = extracts.get("pages") if isinstance(extracts, dict) else None
    if not isinstance(pages, list):
        raise EvidenceAuditError("Extracts input must contain a pages array.")

    page_by_url = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        for field in ("requested_url", "final_url", "canonical_url", "url"):
            key = normalize_url(page.get(field, ""))
            if key:
                page_by_url.setdefault(key, page)

    source_by_id = {str(row.get("id")): row for row in dossier["sources"] if isinstance(row, dict) and row.get("id")}
    audited = []
    for claim in dossier["claims"]:
        cid = str(claim.get("id", ""))
        terms = list(dict.fromkeys(tokens(claim.get("claim", ""))))
        source_results = []
        all_excerpts = []
        for sid in claim.get("source_ids", []):
            source = source_by_id.get(str(sid))
            if not source:
                source_results.append({"source_id": sid, "status": "source_id_missing"})
                continue
            page = page_by_url.get(normalize_url(source.get("url", "")))
            if not page:
                source_results.append({"source_id": sid, "status": "source_not_extracted", "url": source.get("url", "")})
                continue
            if page.get("extraction_status") == "failed":
                source_results.append({"source_id": sid, "status": "extraction_failed", "url": source.get("url", ""), "error": page.get("error", "")})
                continue
            excerpt_rows = excerpts_for(page.get("extracted_text", ""), terms)
            row = {
                "source_id": sid,
                "status": "supported_candidate" if excerpt_rows else "no_matching_excerpt",
                "url": source.get("url", ""),
                "page_title": page.get("page_title", ""),
                "matched_excerpt_count": len(excerpt_rows),
                "excerpts": excerpt_rows,
            }
            source_results.append(row)
            all_excerpts.extend(excerpt_rows)
        found = sum(row.get("status") == "supported_candidate" for row in source_results)
        audited.append({
            "claim_id": cid,
            "claim": claim.get("claim", ""),
            "existing_status_unchanged": claim.get("status", ""),
            "audit_status": "matching_text_found" if found else "no_matching_text_found",
            "source_results": source_results,
            "warning": "Lexical overlap is not proof of support, accuracy, context, or source independence.",
        })

    report = {
        "schema_version": 1,
        "topic": dossier.get("topic", ""),
        "audit_type": "lexical_evidence_locator_not_fact_check",
        "claim_count": len(audited),
        "claims_with_matching_text": sum(row["audit_status"] == "matching_text_found" for row in audited),
        "claims_without_matching_text": sum(row["audit_status"] == "no_matching_text_found" for row in audited),
        "claims": audited,
        "warning": "This audit does not verify truth, infer contradictions, change claim statuses, or authorize narration. Editors must inspect full source context.",
    }
    out = Path(json_output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# Research evidence audit: {report['topic']}", "",
        f"- Claims audited: {report['claim_count']}",
        f"- Claims with matching text: {report['claims_with_matching_text']}",
        f"- Claims without matching text: {report['claims_without_matching_text']}",
        "- Audit type: lexical locator only; not fact-checking.", "",
    ]
    for row in audited:
        lines.extend([f"## {row['claim_id']} — {row['audit_status']}", row["claim"],
                      f"Existing dossier status (unchanged): {row['existing_status_unchanged']}", ""])
        for source in row["source_results"]:
            lines.append(f"- {source['source_id']}: {source['status']} — {source.get('url', '')}")
            for excerpt in source.get("excerpts", []):
                lines.append(f"  - Matched terms: {', '.join(excerpt['matched_terms'])}")
                lines.append(f"  - Excerpt: {excerpt['excerpt']}")
        lines.append("")
    lines.extend(["> " + report["warning"], ""])
    Path(markdown_output).parent.mkdir(parents=True, exist_ok=True)
    Path(markdown_output).write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dossier", required=True)
    parser.add_argument("--extracts", required=True)
    parser.add_argument("--output", default="longform-output/research-evidence-audit.json")
    parser.add_argument("--report", default="longform-output/research-evidence-audit.md")
    args = parser.parse_args()
    try:
        result = audit_research_evidence(args.dossier, args.extracts, args.output, args.report)
    except EvidenceAuditError as exc:
        raise SystemExit(f"RESEARCH_EVIDENCE_AUDIT_FAILED: {exc}") from exc
    print(f"RESEARCH_EVIDENCE_AUDIT_COMPLETE {result['claims_with_matching_text']}/{result['claim_count']} claims have lexical matches")


if __name__ == "__main__":
    main()
