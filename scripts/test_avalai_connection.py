#!/usr/bin/env python3
"""Safe AvalAI connectivity check. Uses GET /models; never sends an inference request."""
import os
import sys
from avalai_client import AvalAIClient, AvalAIError
from free_model_router import is_explicitly_free


def main():
    if not os.getenv("AVALAI_API_KEY", "").strip():
        print("AVALAI_CONNECTION_SKIPPED: AVALAI_API_KEY is not configured; no network request made.")
        return 0
    try:
        client = AvalAIClient()
        rows = client.list_models()
        requested = os.getenv("AVALAI_MODEL", "").strip()
        available = {str(row.get("id") or row.get("name")) for row in rows if isinstance(row, dict)}
        if requested and requested not in available:
            print("AVALAI_CONNECTION_OK: catalogue reachable; configured model ID not listed.")
            return 2
        free = [str(row.get("id") or row.get("name")) for row in rows
                if isinstance(row, dict) and is_explicitly_free(row.get("id") or row.get("name"), row)]
        print(f"AVALAI_CONNECTION_OK: authenticated catalogue reachable; models={len(rows)}; explicitly_free={len(free)}.")
        if requested:
            match = next((row for row in rows if isinstance(row, dict) and
                          str(row.get("id") or row.get("name")) == requested), {})
            if is_explicitly_free(requested, match):
                print("AVALAI_CONFIGURED_MODEL_IS_EXPLICITLY_FREE=true")
            else:
                print("AVALAI_CONFIGURED_MODEL_IS_EXPLICITLY_FREE=false; excluded from zero-cost routing.")
        return 0
    except AvalAIError as exc:
        if "HTTP 429" in str(exc):
            print("AVALAI_CONNECTION_RATE_LIMITED: AvalAI responded with HTTP 429; authentication and model catalogue remain unverified. Retry later.")
            return 0
        print("AVALAI_CONNECTION_FAILED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
