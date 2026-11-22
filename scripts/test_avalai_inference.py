#!/usr/bin/env python3
"""Minimal AvalAI inference smoke test restricted to explicitly zero-priced chat-capable models."""
from __future__ import annotations

import os

from avalai_client import AvalAIClient, AvalAIError
from free_model_router import is_explicitly_free, is_chat_capable

PREFERRED = ("gpt", "qwen", "llama", "gemma", "deepseek", "mistral", "phi")


def free_chat_candidates(rows, requested):
    candidates = []
    free_rows = 0
    excluded_rows = 0
    modality_rows = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = str(row.get("id") or row.get("name") or "").strip()
        if not model_id:
            continue
        explicitly_free = is_explicitly_free(model_id, row)
        if explicitly_free:
            free_rows += 1
        if not is_chat_capable(model_id, row):
            excluded_rows += 1
            architecture = row.get("architecture")
            if isinstance(architecture, dict):
                modality = str(architecture.get("modality") or "").lower()
                if modality and "text" not in modality:
                    modality_rows += 1
            continue
        if explicitly_free:
            candidates.append(model_id)

    if requested:
        if requested not in candidates:
            raise AvalAIError(
                "Configured AVALAI_MODEL is not explicitly free and chat-capable in the live catalogue."
            )
        return [requested], {
            "free_rows": free_rows,
            "excluded_rows": excluded_rows,
            "non_text_modality_rows": modality_rows,
        }
    candidates.sort(key=lambda value: (
        next((len(PREFERRED) - i for i, word in enumerate(PREFERRED) if word in value.lower()), 0),
        value.lower(),
    ), reverse=True)
    return candidates, {
        "free_rows": free_rows,
        "excluded_rows": excluded_rows,
        "non_text_modality_rows": modality_rows,
    }


def main():
    if not os.getenv("AVALAI_API_KEY", "").strip():
        print("AVALAI_INFERENCE_SKIPPED: AVALAI_API_KEY is not configured.")
        return 2
    try:
        client = AvalAIClient(timeout=45, max_retries=1)
        rows = client.list_models()
        candidates, diagnostics = free_chat_candidates(
            rows, os.getenv("AVALAI_MODEL", "").strip()
        )
        print(
            "AVALAI_INFERENCE_CATALOGUE: "
            f"catalogue_models={len(rows)}; explicitly_free={diagnostics['free_rows']}; "
            f"excluded_task_models={diagnostics['excluded_rows']}; "
            f"non_text_modality_models={diagnostics['non_text_modality_rows']}; "
            f"free_chat_candidates={len(candidates)}; "
            f"max_candidates_to_test={os.getenv('AVALAI_MAX_FREE_CHAT_CANDIDATES', '12')}",
            flush=True,
        )
        if candidates:
            print("AVALAI_CHAT_CANDIDATE_IDS: " + ", ".join(candidates[:max(1, min(int(os.getenv("AVALAI_MAX_FREE_CHAT_CANDIDATES", "12")), 12))]), flush=True)
        if not candidates:
            raise AvalAIError(
                "No explicitly free text-chat candidate remains after modality filtering."
            )

        # Try several explicitly-free chat models in rank order. A model outage or
        # unsupported endpoint must not prevent trying the next free model.
        try:
            max_candidates = max(1, min(int(os.getenv("AVALAI_MAX_FREE_CHAT_CANDIDATES", "12")), 12))
        except ValueError:
            max_candidates = 12
        failures = []
        for model in candidates[:max_candidates]:
            print(f"AVALAI_INFERENCE_ATTEMPT: model={model}", flush=True)
            try:
                answer = client.chat_completion(
                    model,
                    [{"role": "user", "content": "Reply with exactly: AVALAI_INFERENCE_OK"}],
                    temperature=0,
                    max_tokens=24,
                )
                if "AVALAI_INFERENCE_OK" not in answer:
                    failures.append(f"{model}: provider returned a non-matching response marker")
                    print(
                        "AVALAI_INFERENCE_UNEXPECTED_RESPONSE: "
                        f"model={model}; continuing to the next explicitly free chat candidate.",
                        flush=True,
                    )
                    continue
                print(
                    "AVALAI_INFERENCE_OK: "
                    f"catalogue_models={len(rows)}; explicitly_free={diagnostics['free_rows']}; "
                    f"tested_model={model}; response_valid=true."
                )
                return 0
            except AvalAIError as exc:
                message = str(exc)
                if "HTTP 429" in message:
                    print(
                        "AVALAI_INFERENCE_RATE_LIMITED: HTTP 429; stopping to respect provider limits."
                    )
                    return 1
                if "HTTP 401" in message or "HTTP 403" in message:
                    print(
                        "AVALAI_INFERENCE_AUTH_FAILED: provider rejected the request; check key permissions and model access."
                    )
                    return 1
                failures.append(f"{model}: {message}")
                print(
                    f"AVALAI_INFERENCE_NEXT_FREE_MODEL: previous_model_failed={model}; "
                    "continuing to the next explicitly free chat candidate.",
                    flush=True,
                )

        print(
            "AVALAI_INFERENCE_FAILED: no tested free candidate completed; "
            + " | ".join(failures)
        )
        return 1
    except AvalAIError as exc:
        message = str(exc)
        if "HTTP 429" in message:
            print(
                "AVALAI_INFERENCE_RATE_LIMITED: HTTP 429; no successful inference was confirmed."
            )
        elif "HTTP 401" in message or "HTTP 403" in message:
            print("AVALAI_INFERENCE_AUTH_FAILED: provider rejected the request.")
        else:
            print("AVALAI_INFERENCE_FAILED: " + message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
