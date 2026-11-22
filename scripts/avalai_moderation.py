#!/usr/bin/env python3
"""Use only explicitly zero-cost AvalAI moderation models as a publication safety gate."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from avalai_client import AvalAIClient, AvalAIError
from free_model_router import is_explicitly_free

PREFERRED_MODELS = (
    "omni-moderation-latest",
    "omni-moderation-2024-09-26",
    "text-moderation-latest",
    "text-moderation-stable",
)


def load_moderation_inputs(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("SEO manifest must be a non-empty JSON array.")
    texts = []
    for index, row in enumerate(payload, 1):
        if not isinstance(row, dict):
            raise ValueError(f"SEO manifest item {index} is malformed.")
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        pieces = [
            str(metadata.get("title") or ""),
            str(metadata.get("description") or ""),
            str(row.get("video_script") or ""),
        ]
        tags = metadata.get("tags")
        if isinstance(tags, list):
            pieces.append(" ".join(str(tag) for tag in tags[:15]))
        text = "\n".join(piece.strip() for piece in pieces if piece.strip())
        if not text:
            raise ValueError(f"SEO manifest item {index} contains no text to moderate.")
        texts.append({"index": index, "topic": str(row.get("topic") or row.get("video_subject") or f"item-{index}"), "text": text})
    return texts


def available_free_moderation_models(rows):
    by_id = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = str(row.get("id") or row.get("name") or "").strip()
        if model_id and "moderation" in model_id.lower() and is_explicitly_free(model_id, row):
            by_id[model_id] = row
    return [model for model in PREFERRED_MODELS if model in by_id]


def write_outputs(report, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    github_output = os.getenv("GITHUB_OUTPUT", "").strip()
    if github_output:
        with open(github_output, "a", encoding="utf-8") as stream:
            stream.write("safe=" + ("true" if report.get("safe_to_publish") else "false") + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="avalai-moderation-report.json")
    args = parser.parse_args()

    items = load_moderation_inputs(Path(args.input))
    base_url = os.getenv("AVALAI_BASE_URL", "https://api.avalai.ir/v1").strip()
    api_key = os.getenv("AVALAI_API_KEY", "").strip()
    report = {
        "schema_version": 1,
        "provider": "AvalAI",
        "status": "UNAVAILABLE",
        "model": None,
        "checked_items": len(items),
        "flagged_items": [],
        "safe_to_publish": False,
        "requires_human_review": True,
        "note": "Moderation is a first-pass safety signal, not a complete safety or factuality review.",
    }

    if not api_key:
        report["status"] = "SKIPPED_NO_API_KEY"
        report["note"] = "AvalAI moderation was not configured; public publishing remains gated."
        write_outputs(report, Path(args.output))
        print("AVALAI_MODERATION_SKIPPED: no API key; public publishing gate remains closed.")
        return 0

    client = AvalAIClient(api_key=api_key, base_url=base_url, timeout=45, max_retries=1)
    try:
        catalogue = client.list_models()
    except AvalAIError as exc:
        report["status"] = "CATALOGUE_UNAVAILABLE"
        report["error"] = str(exc)
        write_outputs(report, Path(args.output))
        print("AVALAI_MODERATION_UNAVAILABLE: catalogue could not be verified; public publishing gate remains closed.")
        return 0

    models = available_free_moderation_models(catalogue)
    if not models:
        report["status"] = "NO_VERIFIED_FREE_MODERATION_MODEL"
        write_outputs(report, Path(args.output))
        print("AVALAI_MODERATION_SKIPPED: no explicitly zero-cost moderation model; public publishing gate remains closed.")
        return 0

    inputs = [item["text"] for item in items]
    failures = []
    for model in models:
        try:
            response = client.moderate(model, inputs)
            results = response["results"]
            flagged = []
            for item, result in zip(items, results):
                categories = result.get("categories") if isinstance(result, dict) else {}
                categories = categories if isinstance(categories, dict) else {}
                flagged_categories = sorted(key for key, value in categories.items() if value is True)
                if result.get("flagged") is True:
                    flagged.append({
                        "index": item["index"],
                        "topic": item["topic"],
                        "categories": flagged_categories,
                    })
            report.update({
                "status": "COMPLETED",
                "model": model,
                "flagged_items": flagged,
                "safe_to_publish": not flagged,
                "requires_human_review": bool(flagged),
                "note": "All items passed the selected moderation model." if not flagged else
                        "One or more items were flagged; human review is required before public release.",
                "route_failures": failures,
            })
            write_outputs(report, Path(args.output))
            print(
                f"AVALAI_MODERATION_COMPLETED: model={model}; checked={len(items)}; "
                f"flagged={len(flagged)}; safe_to_publish={str(not flagged).lower()}",
                flush=True,
            )
            return 0
        except AvalAIError as exc:
            message = str(exc)
            failures.append({"model": model, "error": message})
            print(f"AVALAI_MODERATION_MODEL_FAILED_NEXT_MODEL: model={model}; {message}", flush=True)
            if any(code in message for code in ("HTTP 401", "HTTP 403", "HTTP 429")):
                break

    report["status"] = "ALL_FREE_MODERATION_ROUTES_FAILED"
    report["route_failures"] = failures
    write_outputs(report, Path(args.output))
    print("AVALAI_MODERATION_UNAVAILABLE: all verified free moderation routes failed; public publishing gate remains closed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("AVALAI_MODERATION_INPUT_ERROR: " + type(exc).__name__)
        raise SystemExit(1)
