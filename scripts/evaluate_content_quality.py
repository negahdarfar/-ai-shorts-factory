#!/usr/bin/env python3
"""Evaluate script/SEO/storyboard quality with explicitly free LLM routes or a local draft-only fallback."""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from avalai_client import AvalAIClient
from free_model_router import discover_free_models


def load_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    if isinstance(payload, dict) and isinstance(payload.get("chapters"), list):
        return payload["chapters"]
    return [payload]


def local_review(items):
    reports = []
    for index, item in enumerate(items, 1):
        row = item if isinstance(item, dict) else {"content": str(item)}
        script = str(row.get("video_script") or row.get("narration") or row.get("script") or "")
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else row
        title = str(metadata.get("title") or row.get("title") or "")
        description = str(metadata.get("description") or "")
        issues = []
        if not title.strip():
            issues.append("Missing title.")
        if script and len(script.split()) < 60:
            issues.append("Script is short; verify target runtime and completeness.")
        if not script:
            issues.append("No narration/script field found for local length check.")
        if not description and "metadata" in row:
            issues.append("Missing description.")
        reports.append({
            "index": index, "score": None, "decision": "NEEDS_HUMAN_REVIEW",
            "script_word_count": len(script.split()), "issues": issues,
            "strengths": [], "factual_accuracy_verified": False,
            "note": "Local structural checks only; no factual claims were verified."
        })
    return reports


def parse_ai(raw, expected):
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Quality model response is not JSON.")
    data = json.loads(raw[start:end + 1])
    rows = data.get("items")
    if not isinstance(rows, list) or len(rows) != expected:
        raise ValueError("Quality response item count does not match input.")
    clean = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError("Quality result item is malformed.")
        score = int(row.get("score", -1))
        decision = str(row.get("decision", "")).upper()
        if not 0 <= score <= 100 or decision not in {"PASS", "REVIEW", "REJECT"}:
            raise ValueError("Quality result contains an invalid score or decision.")
        clean.append({
            "index": index, "score": score, "decision": decision,
            "issues": [str(x)[:300] for x in row.get("issues", [])[:10]],
            "strengths": [str(x)[:300] for x in row.get("strengths", [])[:10]],
            "factual_accuracy_verified": False,
            "note": "AI editorial assessment only; this is not independent fact-checking."
        })
    return clean


def request_free(provider, base, key, model, prompt):
    messages = [
        {"role": "system", "content": "You are a strict video editorial quality reviewer. Return valid JSON only. Never claim to verify facts."},
        {"role": "user", "content": prompt}
    ]
    if provider == "AvalAI":
        return AvalAIClient(api_key=key, base_url=base).chat_completion(
            model, messages, temperature=0.1, max_tokens=5000,
            response_format={"type": "json_object"})
    payload = {"model": model, "messages": messages, "temperature": 0.1,
               "max_tokens": 5000, "response_format": {"type": "json_object"}}
    request = urllib.request.Request(base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Free provider returned no choices.")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content)


def routes():
    result = []
    avalai_key = os.getenv("AVALAI_API_KEY", "").strip()
    if avalai_key:
        base = os.getenv("AVALAI_BASE_URL", "https://api.avalai.ir/v1").strip()
        try:
            result += [("AvalAI", base, avalai_key, model) for model in discover_free_models(
                base, avalai_key, task="general", preferred=os.getenv("AVALAI_MODEL", "auto"))]
        except Exception as exc:
            print("AvalAI quality route discovery failed: " + type(exc).__name__, file=sys.stderr)
    free_base = os.getenv("FREELLMAPI_BASE_URL", "").strip()
    free_key = os.getenv("FREELLMAPI_API_KEY", "").strip()
    if free_base and free_key:
        try:
            result += [("FreeLLMAPI", free_base, free_key, model) for model in discover_free_models(
                free_base, free_key, task="general", preferred=os.getenv("FREELLMAPI_MODEL", "auto"))]
        except Exception as exc:
            print("FreeLLMAPI quality route discovery failed: " + type(exc).__name__, file=sys.stderr)
    router_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if router_key:
        base = "https://openrouter.ai/api/v1"
        try:
            result += [("OpenRouter", base, router_key, model) for model in discover_free_models(
                base, router_key, task="general", preferred=os.getenv("OPENROUTER_MODEL", "auto"))]
        except Exception as exc:
            print("OpenRouter quality route discovery failed: " + type(exc).__name__, file=sys.stderr)
    return result


def evaluate(input_path, output_path):
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    items = load_items(payload)
    if not items or len(items) > 100:
        raise ValueError("Input must contain 1-100 content items.")
    compact = json.dumps(items, ensure_ascii=False)
    if len(compact) > 100000:
        raise ValueError("Input exceeds the 100,000-character editorial review limit.")
    prompt = (
        "Assess each video content item for audience hook, clarity, narrative structure, specificity, "
        "subtitle readability, SEO alignment, and responsible factual language. Do not invent facts or "
        "claim external fact verification. Treat unsupported statistics, quotations, and definitive claims "
        "as issues requiring source review. Return JSON {items:[{score:0-100,decision:PASS|REVIEW|REJECT,"
        "issues:[...],strengths:[...]}]}. PASS means editorially ready for human/source review, not approved "
        "for automatic public publishing. Use REVIEW when source support or rights context is uncertain. "
        "Input items:\n" + compact
    )
    selected = None
    errors = []
    for provider, base, key, model in routes():
        try:
            reports = parse_ai(request_free(provider, base, key, model, prompt), len(items))
            selected = (provider, model, reports)
            break
        except Exception as exc:
            errors.append(provider + "/" + model + ":" + type(exc).__name__)
            print("QUALITY_ROUTE_FAILED provider=" + provider + " model=" + model +
                  " error=" + type(exc).__name__, file=sys.stderr)
    if selected:
        provider, model, reports = selected
        status = "AI_EDITORIAL_REVIEW"
    else:
        provider, model, reports = "local_structural_checks", None, local_review(items)
        status = "LOCAL_FALLBACK_NEEDS_HUMAN_REVIEW"
    result = {
        "schema_version": 1, "status": status, "provider": provider, "model": model,
        "items": reports, "all_factual_claims_independently_verified": False,
        "route_failures": errors,
        "publication_policy": "This report never authorizes or triggers YouTube publication."
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CONTENT_QUALITY_REPORT_READY provider=" + provider + " items=" + str(len(reports)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="content-quality-report.json")
    args = parser.parse_args()
    evaluate(args.input, args.output)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Content quality evaluation failed: " + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
