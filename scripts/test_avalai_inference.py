#!/usr/bin/env python3
"""Minimal AvalAI inference smoke test restricted to explicitly zero-priced models."""
from __future__ import annotations

import os

from avalai_client import AvalAIClient, AvalAIError
from free_model_router import is_explicitly_free

EXCLUDED = ("embed", "embedding", "whisper", "transcrib", "transcription", "scribe", "diariz", "speech", "stt", "tts", "text-to-speech", "audio", "image", "vision", "rerank", "ranker", "moderation", "search", "tavily", "browser", "web-search")
PREFERRED = ("gpt", "qwen", "llama", "gemma", "deepseek", "mistral", "phi")


def free_chat_candidates(rows, requested):
    candidates = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = str(row.get("id") or row.get("name") or "").strip()
        if not model_id or any(word in model_id.lower() for word in EXCLUDED):
            continue
        architecture = row.get("architecture")
        if isinstance(architecture, dict):
            modality = str(architecture.get("modality") or "").lower()
            if modality and "text" not in modality:
                continue
        if is_explicitly_free(model_id, row):
            candidates.append(model_id)

    if requested:
        if requested not in candidates:
            raise AvalAIError("Configured AVALAI_MODEL is not explicitly free for text in the live catalogue.")
        return [requested]
    candidates.sort(key=lambda value: (
        next((len(PREFERRED) - i for i, word in enumerate(PREFERRED) if word in value.lower()), 0),
        value.lower(),
    ), reverse=True)
    return candidates


def main():
    if not os.getenv("AVALAI_API_KEY", "").strip():
        print("AVALAI_INFERENCE_SKIPPED: AVALAI_API_KEY is not configured.")
        return 2
    try:
        client = AvalAIClient(timeout=45, max_retries=1)
        rows = client.list_models()
        free_count = sum(
            1 for row in rows if isinstance(row, dict)
            and is_explicitly_free(row.get("id") or row.get("name"), row)
        )
        candidates = free_chat_candidates(rows, os.getenv("AVALAI_MODEL", "").strip())
        if not candidates:
            raise AvalAIError("No explicitly free text-generation candidate was found.")

        # Try at most three catalogue-declared free candidates; never fall back to paid models.
        failures = []
        for model in candidates[:3]:
            print(f"AVALAI_INFERENCE_ATTEMPT: model={model}", flush=True)
            try:
                answer = client.chat_completion(
                    model,
                    [{"role": "user", "content": "Reply with exactly: AVALAI_INFERENCE_OK"}],
                    temperature=0,
                    max_tokens=24,
                )
                if "AVALAI_INFERENCE_OK" not in answer:
                    print("AVALAI_INFERENCE_UNEXPECTED_RESPONSE: provider returned text but not the expected marker.")
                    return 1
                print(f"AVALAI_INFERENCE_OK: catalogue_models={len(rows)}; explicitly_free={free_count}; tested_model={model}; response_valid=true.")
                return 0
            except AvalAIError as exc:
                message = str(exc)
                if "HTTP 429" in message:
                    print("AVALAI_INFERENCE_RATE_LIMITED: HTTP 429; stopping to respect provider limits.")
                    return 1
                if "HTTP 401" in message or "HTTP 403" in message:
                    print("AVALAI_INFERENCE_AUTH_FAILED: provider rejected the request; check key permissions and model access.")
                    return 1
                failures.append(f"{model}: {message}")

        print("AVALAI_INFERENCE_FAILED: no tested free candidate completed; " + " | ".join(failures))
        return 1
    except AvalAIError as exc:
        message = str(exc)
        if "HTTP 429" in message:
            print("AVALAI_INFERENCE_RATE_LIMITED: HTTP 429; no successful inference was confirmed.")
        elif "HTTP 401" in message or "HTTP 403" in message:
            print("AVALAI_INFERENCE_AUTH_FAILED: provider rejected the request.")
        else:
            print("AVALAI_INFERENCE_FAILED: " + message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
