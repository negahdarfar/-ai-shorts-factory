#!/usr/bin/env python3
"""Safe bridge from a video-factory evidence pack to KOROUSH CENTRAL AI.

The central workflow performs research/classification/synthesis/optional
translation only. It does not render, upload, publish, fetch source URLs, or
execute code. Secrets are read only from environment variables.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def request_json(url: str, *, method: str, headers: dict[str, str], body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read(1024).decode("utf-8", errors="replace")
        except Exception:
            pass
        raise RuntimeError(f"Central API returned HTTP {exc.code}: {detail[:300]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Central API transport failed: {type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Central API returned a non-object response")
    return payload


def load_evidence(path: str | None, inline_json: str | None) -> list[dict]:
    if bool(path) == bool(inline_json):
        raise ValueError("Provide exactly one evidence source: --evidence-file or --evidence-json")
    if inline_json:
        raw = json.loads(inline_json)
    else:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    evidence = raw.get("evidence") if isinstance(raw, dict) else raw
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 8:
        raise ValueError("Evidence must contain 1 to 8 items (array or {evidence: [...]})")
    seen: set[str] = set()
    normalized: list[dict] = []
    total_chars = 0
    allowed = {"source_id", "text", "publisher", "source_url", "observed_at"}
    for index, item in enumerate(evidence):
        if not isinstance(item, dict) or set(item) - allowed:
            raise ValueError(f"Evidence item {index + 1} contains an invalid shape or unsupported fields")
        source_id, text = item.get("source_id"), item.get("text")
        if not isinstance(source_id, str) or not source_id.strip() or len(source_id) > 128:
            raise ValueError(f"Evidence item {index + 1} requires source_id (1–128 characters)")
        if source_id in seen:
            raise ValueError("Evidence source_id values must be unique")
        seen.add(source_id)
        if not isinstance(text, str) or not text.strip() or len(text) > 5000:
            raise ValueError(f"Evidence item {index + 1} requires text (1–5000 characters)")
        total_chars += len(text)
        record = {"source_id": source_id.strip(), "text": text.strip()}
        for key in ("publisher", "source_url", "observed_at"):
            value = item.get(key)
            if value is not None:
                if not isinstance(value, str) or len(value) > 2048:
                    raise ValueError(f"Evidence item {index + 1}: {key} must be text up to 2048 characters")
                record[key] = value
        normalized.append(record)
    if total_chars > 20000:
        raise ValueError("Combined evidence text exceeds the central 20,000-character limit")
    return normalized


def resolve_integration(
    base_url: str, headers: dict[str, str], integration_id: str, *, require_translation: bool = True
) -> tuple[str, dict, dict]:
    """Sync the public core manifest and resolve a built-in or registered connector."""
    manifest = request_json(base_url + "/api/platform/manifest", method="GET", headers=headers)
    agents = manifest.get("agents", [])
    providers = manifest.get("providers", [])
    source_connectors = manifest.get("source_connectors", [])
    if not isinstance(agents, list) or not isinstance(providers, list) or not isinstance(source_connectors, list):
        raise RuntimeError("Central manifest has an unsupported schema; refusing to use a stale local catalog")
    agent_ids = {item.get("id") for item in agents if isinstance(item, dict)}
    required_agents = {"koroush.research-brief", "koroush.text-classifier", "koroush.text-summarizer"}
    if require_translation:
        required_agents.add("koroush.text-translator")
    missing = sorted(required_agents - agent_ids)
    if missing:
        raise RuntimeError("Central manifest is missing required agents: " + ", ".join(missing))
    catalog = request_json(base_url + "/api/integrations", method="GET", headers=headers)
    profiles = catalog.get("integrations", [])
    connectors = catalog.get("registered_connectors", [])
    if not isinstance(profiles, list) or not isinstance(connectors, list):
        raise RuntimeError("Central integration catalog has an unsupported response shape")

    if integration_id == "youtube":
        match = next((x for x in profiles if isinstance(x, dict) and x.get("id") == "koroush.youtube"), None)
        if not match:
            raise RuntimeError("Central core does not advertise the built-in YouTube research profile")
        return "youtube", match, manifest

    if not re.fullmatch(r"[a-z][a-z0-9]*(?:[.-][a-z0-9]+){1,7}", integration_id) or len(integration_id) > 100:
        raise ValueError("integration-id must be 'youtube' or a registered connector ID")
    match = next((
        x for x in connectors
        if isinstance(x, dict) and x.get("id") == integration_id and x.get("status") == "active"
        and "general" in x.get("domains", [])
        and "research.workflow.v1" in x.get("capabilities", [])
    ), None)
    if not match:
        raise RuntimeError(f"Connector '{integration_id}' is not active/compatible in the central catalog")
    return integration_id, match, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integration-id", default=os.getenv("KOROUSH_CENTRAL_INTEGRATION_ID", "youtube"))
    parser.add_argument("--evidence-file", default=os.getenv("KOROUSH_CENTRAL_EVIDENCE_FILE"))
    parser.add_argument("--evidence-json", default=os.getenv("KOROUSH_CENTRAL_EVIDENCE_JSON"))
    parser.add_argument("--idempotency-key", default=os.getenv("KOROUSH_CENTRAL_IDEMPOTENCY_KEY"))
    parser.add_argument("--target-language", default=os.getenv("KOROUSH_CENTRAL_TARGET_LANGUAGE", "Persian"))
    parser.add_argument("--wait-seconds", type=int, default=480)
    args = parser.parse_args()

    base_url = os.getenv("KOROUSH_CENTRAL_BASE_URL", "").strip().rstrip("/")
    tenant_key = os.getenv("KOROUSH_CENTRAL_TENANT_KEY", "")
    repository = os.getenv("GITHUB_REPOSITORY", "").strip().lower()
    if not base_url.startswith("https://") or not tenant_key.startswith("kor_") or not repository:
        raise ValueError("Set HTTPS KOROUSH_CENTRAL_BASE_URL, KOROUSH_CENTRAL_TENANT_KEY and GITHUB_REPOSITORY")
    if not args.idempotency_key or not 1 <= len(args.idempotency_key) <= 128:
        raise ValueError("A stable idempotency-key (1–128 characters) is required")
    if not 1 <= args.wait_seconds <= 1800:
        raise ValueError("wait-seconds must be between 1 and 1800")
    evidence = load_evidence(args.evidence_file, args.evidence_json)

    headers = {"X-Tenant-Key": tenant_key, "Content-Type": "application/json", "Accept": "application/json"}
    route, profile, manifest = resolve_integration(
        base_url, headers, args.integration_id, require_translation=bool(args.target_language)
    )
    body = {
        "repository": repository,
        "idempotency_key": args.idempotency_key,
        "evidence": evidence,
        "max_attempts": 3,
    }
    if args.target_language:
        body["target_language"] = args.target_language
    url = base_url + "/api/integrations/" + urllib.parse.quote(route, safe=".-") + "/research"
    submitted = request_json(url, method="POST", headers=headers, body=body)
    job_id, status_api = submitted.get("job_id"), submitted.get("status_api")
    if not isinstance(job_id, str) or not job_id or not isinstance(status_api, str):
        raise RuntimeError("Central API response did not contain a job ID and status reference")
    parsed_status = urllib.parse.urlsplit(status_api)
    if parsed_status.scheme or parsed_status.netloc or not parsed_status.path.startswith("/api/jobs/") or ".." in parsed_status.path.split("/"):
        raise RuntimeError("Central API returned an unsafe job status reference")

    active_providers = [x.get("id") for x in manifest.get("providers", []) if isinstance(x, dict) and x.get("status") == "available"]
    listed_sources = [x.get("id") for x in manifest.get("source_connectors", []) if isinstance(x, dict)]
    print(f"Central integration: {profile.get('id', args.integration_id)}")
    print("Central agent catalog synchronized: research-brief, classifier, summarizer" + (", translator" if args.target_language else ""))
    print(f"Central available providers: {', '.join(active_providers) if active_providers else 'none marked available'}")
    print(f"Central source connector catalog entries: {len(listed_sources)} (discovery metadata only)")
    print(f"Central job accepted: {job_id} ({submitted.get('status', 'unknown')})")
    deadline = time.monotonic() + args.wait_seconds
    while time.monotonic() < deadline:
        status_url = base_url + status_api
        status = request_json(status_url, method="GET", headers=headers)
        state = status.get("status")
        print(f"Central job state: {state}")
        if state == "succeeded":
            result = status.get("result")
            if isinstance(result, dict):
                print(json.dumps(result, ensure_ascii=False, indent=2)[:12000])
            return 0
        if state in {"failed", "dead_letter", "cancelled"}:
            raise RuntimeError(f"Central job ended with state: {state}")
        time.sleep(5)
    raise TimeoutError(f"Central job {job_id} did not finish within {args.wait_seconds} seconds")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Central integration failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
