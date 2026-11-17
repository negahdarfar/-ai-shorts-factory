#!/usr/bin/env python3
"""Discover and rank explicitly free OpenAI-compatible models from FreeLLMAPI.

Discovery only calls GET /models (no inference). A model is eligible only when
its public ID explicitly advertises a free tier; unknown pricing is never assumed free.
"""
import json
import os
import urllib.error
import urllib.request

FREE_MARKERS = (":free", "/free", "-free", "_free")
ROUTER_MARKERS = ("kilo-auto/free", "openrouter/free")


def is_explicitly_free(model_id):
    value = str(model_id or "").strip().lower()
    return bool(value) and any(marker in value for marker in FREE_MARKERS)


def _model_ids(payload):
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        raise RuntimeError("FreeLLMAPI /models response has no model list.")
    result = []
    for row in rows:
        if isinstance(row, dict):
            model_id = row.get("id") or row.get("name")
            if model_id and is_explicitly_free(model_id):
                result.append(str(model_id))
    return list(dict.fromkeys(result))


def _score(model_id, task):
    value = model_id.lower()
    if value in ROUTER_MARKERS:
        return -100
    score = 0
    if task == "translation":
        for marker, points in (
            ("lightning", 100), ("flash", 85), ("mini", 70),
            ("nano", 60), ("instruct", 45), ("super", 35),
            ("ultra", 25), ("reason", 20),
        ):
            if marker in value:
                score += points
    elif task == "seo":
        for marker, points in (
            ("super", 100), ("ultra", 90), ("reason", 85),
            ("instruct", 70), ("flash", 60), ("lightning", 50),
            ("mini", 40), ("nano", 30),
        ):
            if marker in value:
                score += points
    elif task == "vision":
        score += 100 if any(x in value for x in ("vision", "-vl", "omni")) else 0
    if any(x in value for x in ("vision", "-vl")) and task != "vision":
        score -= 50
    return score


def discover_free_models(base_url, api_key, task="general", preferred="auto", timeout=20):
    """Return best-first free model IDs from the live gateway catalogue."""
    if not base_url or not api_key:
        return []
    url = base_url.rstrip("/") + "/models"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"FreeLLMAPI model discovery failed: {exc}") from exc

    models = _model_ids(payload)
    if not models:
        return []
    preferred = str(preferred or "auto").strip()
    ordered = sorted(models, key=lambda item: (_score(item, task), item.lower()), reverse=True)
    if preferred.lower() not in ("", "auto") and preferred in models:
        ordered = [preferred] + [item for item in ordered if item != preferred]
    return ordered


def free_only_enabled():
    """Paid/unpriced routes remain blocked unless a future explicit opt-in is added."""
    return os.getenv("FREELLMAPI_ALLOW_UNPRICED_MODELS", "false").strip().lower() == "true"
