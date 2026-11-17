#!/usr/bin/env python3
"""Translate generated English SRT captions to Persian and burn them in above the English captions."""
import argparse
import json
import http.client
import socket
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from free_model_router import discover_free_models

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
RETRYABLE_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}
SRT_BLOCK = re.compile(r"(?ms)^\s*(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3})\s*\n(.*?)(?=\n\s*\n|\Z)")


def parse_srt(path):
    raw = path.read_text(encoding="utf-8-sig")
    rows = []
    for match in SRT_BLOCK.finditer(raw):
        cue = " ".join(line.strip() for line in match.group(3).splitlines() if line.strip())
        if cue:
            rows.append({"index": int(match.group(1)), "timing": match.group(2), "text": cue})
    if not rows:
        raise RuntimeError(f"No readable subtitle cues in {path}")
    return rows


def parse_translation_json(raw, rows, provider):
    cleaned = raw.strip()
    fence = chr(96) * 3
    cleaned = cleaned.removeprefix(fence).removesuffix(fence).strip()
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError(f"{provider} did not return a JSON translation object.")
    parsed = json.loads(cleaned[start:end + 1])
    mapping = {
        int(row["index"]): str(row["text"]).strip()
        for row in parsed.get("translations", [])
    }
    expected = {row["index"] for row in rows}
    if set(mapping) != expected or any(not mapping[index] for index in expected):
        raise RuntimeError(f"{provider} returned missing or empty subtitle cues.")
    return mapping


def post_json_with_retry(url, payload, headers, provider, max_attempts, timeout, base_delay):
    request_data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            url,
            data=request_data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            if exc.code not in RETRYABLE_HTTP_STATUSES or attempt >= max_attempts:
                raise RuntimeError(
                    f"{provider} request failed after {attempt} attempt(s): "
                    f"HTTP {exc.code}: {detail}"
                ) from exc
            retry_after = 0.0
            try:
                retry_after = float(exc.headers.get("Retry-After", "0"))
            except (TypeError, ValueError):
                pass
            delay = min(180.0, max(base_delay * (2 ** (attempt - 1)), retry_after))
            print(
                f"{provider.upper()}_TEMPORARY_HTTP_{exc.code}; "
                f"retry {attempt + 1}/{max_attempts} in {delay:.0f}s",
                flush=True,
            )
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError, socket.timeout, http.client.HTTPException, ConnectionError) as exc:
            if attempt >= max_attempts:
                raise RuntimeError(
                    f"{provider} connection failed after {attempt} attempt(s): {exc}"
                ) from exc
            delay = min(180.0, base_delay * (2 ** (attempt - 1)))
            print(
                f"{provider.upper()}_TEMPORARY_CONNECTION_OR_READ_ERROR; "
                f"retry {attempt + 1}/{max_attempts} in {delay:.0f}s",
                flush=True,
            )
            time.sleep(delay)
    raise RuntimeError(f"{provider} request ended without a response.")


def translate_gemini(rows, model, key):
    prompt = (
        "Translate each English subtitle cue into natural, concise Persian (Farsi). Preserve meaning, names, numbers, and tone. "
        'Return ONLY JSON: {"translations":[{"index":1,"text":"..."}]}. '
        "Return exactly one translation for every input index, in order. Do not merge cues or add explanations. "
        "Keep each Persian cue short enough to read on a phone. Input cues: "
        + json.dumps(rows, ensure_ascii=False)
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    max_attempts = max(1, int(os.getenv("GEMINI_SUBTITLE_MAX_ATTEMPTS", "8")))
    base_delay = max(1.0, float(os.getenv("GEMINI_SUBTITLE_RETRY_BASE_SECONDS", "15")))
    response_data = post_json_with_retry(
        f"{API_ROOT}/{model}:generateContent?key={key}",
        payload,
        {"Content-Type": "application/json"},
        "Gemini",
        max_attempts,
        300,
        base_delay,
    )
    parts = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    raw = "\n".join(part.get("text", "") for part in parts)
    return parse_translation_json(raw, rows, "Gemini")


def translate_omniroute(rows, base_url, key, model):
    prompt = (
        "Translate each English subtitle cue into natural, concise Persian (Farsi). Preserve meaning, names, numbers, and tone. "
        'Return ONLY valid JSON with this exact shape: {"translations":[{"index":1,"text":"..."}]}. '
        "Return exactly one translation for every input index, in order. Do not merge cues or add explanations. "
        "Keep each Persian cue short enough to read on a phone. Input cues: "
        + json.dumps(rows, ensure_ascii=False)
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a professional English-to-Persian subtitle translator. Output only the requested JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    max_attempts = max(1, int(os.getenv("OMNIROUTE_MAX_ATTEMPTS", "3")))
    timeout = max(30, int(os.getenv("OMNIROUTE_TIMEOUT_SECONDS", "180")))
    base_delay = max(1.0, float(os.getenv("OMNIROUTE_RETRY_BASE_SECONDS", "15")))
    response_data = post_json_with_retry(
        base_url.rstrip("/") + "/chat/completions",
        payload,
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        "OmniRoute",
        max_attempts,
        timeout,
        base_delay,
    )
    choices = response_data.get("choices", [])
    if not choices:
        raise RuntimeError("OmniRoute returned no chat completion choices.")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        raw = "\n".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    else:
        raw = str(content)
    return parse_translation_json(raw, rows, "OmniRoute")


def translate_cloudflare(rows, base_url, key, model):
    prompt = (
        "Translate each English subtitle cue into natural, concise Persian (Farsi). Preserve meaning, names, numbers, and tone. "
        'Return ONLY valid JSON with this exact shape: {"translations":[{"index":1,"text":"..."}]}. '
        "Return exactly one translation for every input index, in order. Do not merge cues or add explanations. "
        "Keep each Persian cue short enough to read on a phone. Input cues: "
        + json.dumps(rows, ensure_ascii=False)
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a professional English-to-Persian subtitle translator. Output only the requested JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    response_data = post_json_with_retry(
        base_url.rstrip("/") + "/chat/completions", payload,
        {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        "Cloudflare Workers AI", 3, 180, 10,
    )
    choices = response_data.get("choices", [])
    if not choices:
        raise RuntimeError("Cloudflare Workers AI returned no chat completion choices.")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        raw = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    else:
        raw = str(content)
    return parse_translation_json(raw, rows, "Cloudflare Workers AI")


def translate_freellmapi(rows, base_url, key, model):
    prompt = (
        "Translate each English subtitle cue into natural, concise Persian (Farsi). Preserve meaning, names, numbers, and tone. "
        'Return ONLY valid JSON with this exact shape: {"translations":[{"index":1,"text":"..."}]}. '
        "Return exactly one translation for every input index, in order. Do not merge cues or add explanations. "
        "Keep each Persian cue short enough to read on a phone. Input cues: "
        + json.dumps(rows, ensure_ascii=False)
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a professional English-to-Persian subtitle translator. Output only the requested JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    response_data = post_json_with_retry(
        base_url.rstrip("/") + "/chat/completions",
        payload,
        {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        "FreeLLMAPI",
        max(1, int(os.getenv("FREELLMAPI_MAX_ATTEMPTS", "3"))),
        max(30, int(os.getenv("FREELLMAPI_TIMEOUT_SECONDS", "180"))),
        max(1.0, float(os.getenv("FREELLMAPI_RETRY_BASE_SECONDS", "15"))),
    )
    choices = response_data.get("choices", [])
    if not choices:
        raise RuntimeError("FreeLLMAPI returned no chat completion choices.")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        raw = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    else:
        raw = str(content)
    return parse_translation_json(raw, rows, "FreeLLMAPI")


def translate_with_fallback(rows, omni, free, gemini, cloudflare=None):
    cloudflare = cloudflare or (\"\", \"\", \"\")
    failures = []
    allow_nonfree_fallback = os.getenv("ALLOW_NONFREE_LLM_FALLBACK", "false").strip().lower() == "true"
    if omni[0] and omni[1] and allow_nonfree_fallback:
        try:
            return translate_omniroute(rows, *omni), "OmniRoute"
        except Exception as exc:
            failures.append(f"OmniRoute: {exc}")
            print(f"OMNIROUTE_FAILED_NEXT_PROVIDER | {exc}", flush=True)
    if cloudflare[0] and cloudflare[1] and cloudflare[2] == "@cf/zai-org/glm-4.7-flash":
        try:
            return translate_cloudflare(rows, cloudflare[0], cloudflare[1], cloudflare[2]), "Cloudflare Workers AI"
        except Exception as exc:
            failures.append(f"Cloudflare Workers AI: {exc}")
            print(f"CLOUDFLARE_FAILED_NEXT_PROVIDER | {exc}", flush=True)
    if free[0] and free[1]:
        try:
            candidates = discover_free_models(
                free[0], free[1], task="translation", preferred=free[2]
            )
        except Exception as exc:
            candidates = []
            failures.append(f"FreeLLMAPI discovery: {exc}")
            print(f"FREELLMAPI_DISCOVERY_FAILED_NEXT_PROVIDER | {exc}", flush=True)
        if not candidates:
            print("FREELLMAPI_NO_EXPLICITLY_FREE_MODELS; skipping gateway to prevent paid or unknown-price routing.", flush=True)
        for model_id in candidates:
            try:
                print(f"FREELLMAPI_AUTO_SELECTED_MODEL={model_id} | task=translation", flush=True)
                return translate_freellmapi(rows, free[0], free[1], model_id), "FreeLLMAPI"
            except Exception as exc:
                failures.append(f"FreeLLMAPI/{model_id}: {exc}")
                print(f"FREELLMAPI_MODEL_FAILED_NEXT_MODEL | model={model_id} | {exc}", flush=True)
    if gemini[0] and allow_nonfree_fallback:
        return translate_gemini(rows, gemini[1], gemini[0]), "Gemini"
    if (omni[0] and omni[1]) or gemini[0]:
        print("NON_FREE_LLM_FALLBACK_DISABLED; paid or unknown-price providers were not called.", flush=True)
    detail = "; ".join(failures) if failures else "No complete provider credentials configured."
    raise RuntimeError(f"All configured subtitle providers failed. {detail}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.getenv("SEO_GEMINI_MODEL", "gemini-3.8-flash"))
    parser.add_argument("--home", default=os.getenv("MPT_HOME", "mpt-runtime"))
    args = parser.parse_args()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    omniroute_base_url = os.getenv("OMNIROUTE_BASE_URL", "").strip()
    omniroute_key = os.getenv("OMNIROUTE_API_KEY", "").strip()
    omniroute_model = os.getenv("OMNIROUTE_MODEL", "auto").strip() or "auto"
    freellmapi_base_url = os.getenv("FREELLMAPI_BASE_URL", "").strip()
    freellmapi_key = os.getenv("FREELLMAPI_API_KEY", "").strip()
    freellmapi_model = os.getenv("FREELLMAPI_MODEL", "auto").strip() or "auto"
    cloudflare_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    cloudflare_api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    cloudflare_model = os.getenv("CLOUDFLARE_MODEL", "@cf/zai-org/glm-4.7-flash").strip()
    cloudflare_base_url = f"https://api.cloudflare.com/client/v4/accounts/{cloudflare_account_id}/ai/v1" if cloudflare_account_id else ""
    cloudflare = (cloudflare_base_url, cloudflare_api_token, cloudflare_model)
    if not (
        (omniroute_base_url and omniroute_key)
        or (freellmapi_base_url and freellmapi_key)
        or (cloudflare_base_url and cloudflare_api_token and cloudflare_model == "@cf/zai-org/glm-4.7-flash")
        or gemini_key
    ):
        raise SystemExit("Configure Cloudflare Workers AI free credentials, a FreeLLMAPI pair, an allowed OmniRoute pair, or GEMINI_API_KEY.")
    if bool(omniroute_base_url) != bool(omniroute_key):
        print("OMNIROUTE_INCOMPLETE_CONFIGURATION; skipping OmniRoute.", flush=True)
    if bool(freellmapi_base_url) != bool(freellmapi_key):
        print("FREELLMAPI_INCOMPLETE_CONFIGURATION; skipping FreeLLMAPI.", flush=True)
    root = Path(args.home) / "storage" / "tasks"
    videos = sorted(root.glob("**/final-*.mp4"))
    if len(videos) != 4:
        raise SystemExit(f"Expected four final videos before Persian subtitle processing, found {len(videos)}.")
    for index, video in enumerate(videos, 1):
        english = video.parent / "subtitle.srt"
        if not english.is_file():
            raise SystemExit(f"English subtitle source missing for video {index}: {english}")
        cues = parse_srt(english)
        translations, provider_used = translate_with_fallback(
            cues,
            (omniroute_base_url, omniroute_key, omniroute_model),
            (freellmapi_base_url, freellmapi_key, freellmapi_model),
            (gemini_key, args.model),
            cloudflare,
        )
        print(f"{provider_used.upper()}_TRANSLATION_SUCCEEDED {index}/4", flush=True)
        persian = video.parent / "subtitle.fa.srt"
        blocks = [
            f"{cue['index']}\n{cue['timing']}\n{translations[cue['index']]}\n"
            for cue in cues
        ]
        persian.write_text("\n".join(blocks), encoding="utf-8")
        temporary = video.with_name(video.stem + ".fa-tmp.mp4")
        escaped = str(persian.resolve()).replace("\\", "/").replace(":", "\\:")
        vf = (
            f"subtitles='{escaped}':force_style='FontName=Noto Naskh Arabic,"
            "FontSize=18,Alignment=8,MarginV=42,Outline=2,Shadow=0,"
            "BorderStyle=3,BackColour=&H90000000'"
        )
        command = [
            "ffmpeg", "-y", "-i", str(video), "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
            str(temporary),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            temporary.unlink(missing_ok=True)
            raise SystemExit(
                f"Persian subtitle burn-in failed for video {index}: "
                f"{(result.stderr or result.stdout)[-2500:]}"
            )
        if not temporary.is_file() or temporary.stat().st_size < 500_000:
            raise SystemExit(f"Persian-subtitled output invalid for video {index}.")
        temporary.replace(video)
        print(f"PERSIAN_SUBTITLES_BURNED_IN {index}/4 | cues={len(cues)} | {video.name}")
    print("PERSIAN_SUBTITLES_COMPLETED_FOR_ALL_FOUR_VIDEOS")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"PERSIAN_SUBTITLE_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
