#!/usr/bin/env python3
"""Small, dependency-free AvalAI OpenAI-compatible client with safe retries."""
from __future__ import annotations
import json
import os
import random
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.avalai.ir/v1"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class AvalAIError(RuntimeError):
    """Safe provider error; never contains request headers, credentials, or response body."""


class AvalAIClient:
    def __init__(self, api_key=None, base_url=None, timeout=45, max_retries=4):
        self.api_key = (api_key if api_key is not None else os.getenv("AVALAI_API_KEY", "")).strip()
        self.base_url = (base_url or os.getenv("AVALAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = max(5, min(int(timeout), 180))
        self.max_retries = max(0, min(int(max_retries), 5))
        if not self.base_url.startswith("https://"):
            raise ValueError("AvalAI base URL must use HTTPS.")

    def _request(self, path, payload=None):
        if not self.api_key:
            raise AvalAIError("AVALAI_API_KEY is not configured.")
        url = self.base_url + "/" + path.lstrip("/")
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Authorization": "Bearer " + self.api_key, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        last_status = None
        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(url, data=data, headers=headers,
                                             method="GET" if data is None else "POST")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read(8 * 1024 * 1024 + 1)
                    if len(raw) > 8 * 1024 * 1024:
                        raise AvalAIError("AvalAI response exceeded the 8 MiB safety limit.")
                    try:
                        return json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise AvalAIError("AvalAI returned an invalid JSON response.") from exc
            except urllib.error.HTTPError as exc:
                last_status = int(exc.code)
                if last_status not in RETRYABLE_STATUS or attempt >= self.max_retries:
                    raise AvalAIError(f"AvalAI request failed with HTTP {last_status}.") from None
                retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                try:
                    delay = float(retry_after)
                except (TypeError, ValueError):
                    delay = 1.5 * (2 ** attempt) + random.uniform(0, 0.25)
                if delay <= 0:
                    delay = 1.5 * (2 ** attempt) + random.uniform(0, 0.25)
                if last_status == 429:
                    delay = max(30.0, delay)
                time.sleep(max(1.0, min(delay, 60.0)))
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt >= self.max_retries:
                    raise AvalAIError(f"AvalAI network request failed ({type(exc).__name__}).") from None
                time.sleep(min(1.5 * (2 ** attempt), 8.0))
        raise AvalAIError(f"AvalAI request failed (HTTP {last_status}).")

    def list_models(self):
        """GET /models only; catalog check does not generate text."""
        payload = self._request("models")
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise AvalAIError("AvalAI model catalogue has an unexpected format.")
        return rows

    def chat_completion(self, model, messages, **options):
        """Create one chat completion. Caller must explicitly select a model."""
        if not str(model or "").strip():
            raise AvalAIError("AVALAI_MODEL is not configured.")
        payload = {"model": model, "messages": messages}
        allowed = {"temperature", "max_tokens", "max_completion_tokens", "response_format",
                   "top_p", "seed", "stop"}
        payload.update({key: value for key, value in options.items() if key in allowed})
        result = self._request("chat/completions", payload)
        choices = result.get("choices") if isinstance(result, dict) else None
        if not isinstance(choices, list) or not choices:
            raise AvalAIError("AvalAI returned no chat completion choices.")
        message = choices[0].get("message", {})
        content = message.get("content", "") if isinstance(message, dict) else ""
        if isinstance(content, list):
            content = "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
        if not str(content).strip():
            raise AvalAIError("AvalAI returned an empty completion.")
        return str(content)
