#!/usr/bin/env python3
"""Discover and rank explicitly free OpenAI-compatible models from FreeLLMAPI.

Discovery only calls GET /models (no inference). A model is eligible only when
its ID or structured catalogue metadata explicitly advertises a free tier, or
all advertised input/output token prices are exactly zero. Unknown pricing is
never assumed free.
"""
import json
import hashlib
import os
import tempfile
import time
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urlparse
from avalai_client import AvalAIClient

FREE_MARKERS = (":free", "/free", "-free", "_free")
ROUTER_MARKERS = ("kilo-auto/free", "openrouter/free")
PRICE_KEYS = (
    ("prompt", "completion"),
    ("input", "output"),
    ("input_cost_per_token", "output_cost_per_token"),
    ("input_price", "output_price"),
)


def _is_zero_price(value):
    if isinstance(value, bool) or value is None:
        return False
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False


def _metadata_is_free(metadata):
    """Recognize only unambiguous, machine-readable free-tier declarations."""
    if not isinstance(metadata, dict):
        return False

    for key in ("is_free", "free", "free_tier"):
        if metadata.get(key) is True:
            return True
    for key in ("pricing", "cost", "prices"):
        pricing = metadata.get(key)
        if isinstance(pricing, dict):
            for input_key, output_key in PRICE_KEYS:
                if input_key in pricing and output_key in pricing:
                    if _is_zero_price(pricing[input_key]) and _is_zero_price(pricing[output_key]):
                        return True
    # Some catalogues put free-tier metadata under a provider object.
    provider = metadata.get("top_provider")
    if isinstance(provider, dict) and _metadata_is_free(provider):
        return True
    return False


def is_explicitly_free(model_id, metadata=None):
    value = str(model_id or "").strip().lower()
    return bool(value) and (
        any(marker in value for marker in FREE_MARKERS)
        or _metadata_is_free(metadata)
    )


NON_CHAT_MARKERS = (
    "search", "serper", "perplexity", "parallel_ai", "tavily", "exa-",
    "browser", "crawler", "scrape", "rerank", "ranker", "embedding",
    "embed", "moderation", "transcrib", "transcription", "tts",
    "text-to-speech", "speech", "audio", "image-generation",
    "text-to-image", "video-generation", "ocr", "stt", "asr",
)


def is_chat_capable(model_id, metadata=None):
    """Conservatively reject tool/task endpoints that are not chat-completion models."""
    value = str(model_id or "").strip().lower()
    if not value or any(marker in value for marker in NON_CHAT_MARKERS):
        return False
    if not isinstance(metadata, dict):
        return True

    architecture = metadata.get("architecture")
    if isinstance(architecture, dict):
        modality = str(architecture.get("modality") or "").lower()
        if modality and "text" not in modality:
            return False

    modalities = metadata.get("modalities")
    if isinstance(modalities, (list, tuple)) and modalities:
        if "text" not in " ".join(str(item).lower() for item in modalities):
            return False

    # Catalogue task/type/description fields can identify search and utility APIs
    # even when the model ID itself looks like a language model.
    descriptive_fields = (
        "task", "tasks", "task_type", "type", "description",
        "capability", "capabilities", "endpoint",
    )
    description = " ".join(
        str(metadata.get(key) or "").lower() for key in descriptive_fields
    )
    return not any(marker in description for marker in NON_CHAT_MARKERS)


def _model_rows(payload):
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        raise RuntimeError("FreeLLMAPI /models response has no model list.")
    return rows


def _model_ids(payload):
    result = []
    for row in _model_rows(payload):
        if isinstance(row, dict):
            model_id = row.get("id") or row.get("name")
            if model_id and is_explicitly_free(model_id, row) and is_chat_capable(model_id, row):
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
    """Return best-first explicitly free model IDs from the live gateway catalogue."""
    if not base_url or not api_key:
        return []
    host = (urlparse(base_url).hostname or "").lower()
    try:
        if host in {"api.avalai.ir", "api.avalapis.ir", "api.avalai.org"}:
            # Cache only the public model/pricing catalogue briefly to stay within
            # AvalAI's low account-tier RPM limits across sequential pipeline steps.
            ttl = max(0, min(int(os.getenv("AVALAI_MODEL_CACHE_TTL_SECONDS", "300")), 3600))
            key_hash = hashlib.sha256((base_url.rstrip("/") + "\\0" + api_key).encode("utf-8")).hexdigest()[:20]
            cache_path = Path(os.getenv("AVALAI_MODEL_CACHE_PATH", str(Path(tempfile.gettempdir()) / ("avalai-models-" + key_hash + ".json"))))
            cached = None
            if ttl and cache_path.is_file() and time.time() - cache_path.stat().st_mtime <= ttl:
                try:
                    cached = json.loads(cache_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    cached = None
            if isinstance(cached, dict) and isinstance(cached.get("data"), list):
                payload = cached
            else:
                payload = {"data": AvalAIClient(api_key=api_key, base_url=base_url, timeout=timeout).list_models()}
                if ttl:
                    try:
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        temporary = cache_path.with_suffix(cache_path.suffix + ".tmp")
                        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                        temporary.replace(cache_path)
                    except OSError:
                        pass
        else:
            url = base_url.rstrip("/") + "/models"
            request = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as exc:
        raise RuntimeError(f"Model catalogue discovery failed ({type(exc).__name__}).") from None

    rows = _model_rows(payload)
    models = _model_ids(payload)
    if not models:
        priced = sum(
            1 for row in rows if isinstance(row, dict)
            and any(isinstance(row.get(key), dict) for key in ("pricing", "cost", "prices"))
        )
        print(
            f"FreeLLMAPI catalogue: {len(rows)} models; {priced} include structured pricing; "
            "none explicitly free. Unknown-price models remain excluded.",
            flush=True,
        )
        return []
    ordered = sorted(models, key=lambda item: (_score(item, task), item.lower()), reverse=True)
    preferred = str(preferred or "auto").strip()
    if preferred.lower() not in ("", "auto") and preferred in models:
        ordered = [preferred] + [item for item in ordered if item != preferred]
    print(f"FreeLLMAPI catalogue: {len(rows)} models; {len(ordered)} explicitly free candidates.", flush=True)
    return ordered
