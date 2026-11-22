#!/usr/bin/env python3
"""Translate SRT to Persian: zero-price AvalAI models first, then existing Gemini fallback."""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from avalai_client import AvalAIClient, AvalAIError
from free_model_router import discover_free_models

API = "https://generativelanguage.googleapis.com/v1beta/models"
BLOCK = re.compile(r"^\s*(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3})\s*\n([\s\S]*?)\s*$")


def parse_srt(text):
    rows = []
    for block in re.split(r"\n\s*\n", text.strip()):
        match = BLOCK.match(block.strip())
        if not match:
            raise ValueError("Malformed SRT block; expected index, timestamp line and caption.")
        rows.append({"index": int(match.group(1)), "time": match.group(2),
                     "text": re.sub(r"\s+", " ", match.group(3)).strip()})
    return rows


def prompt_for(rows):
    return ("Translate these English subtitle lines into natural, concise Persian (Farsi). "
            "Preserve meaning, names, numbers and tone. Do not add explanations. Return ONLY JSON "
            "with a single key 'translations' containing exactly one Persian string per input line. "
            "Do not merge or split captions. Input JSON:\n"
            + json.dumps([row["text"] for row in rows], ensure_ascii=False))


def parse_translations(raw, rows):
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Translation response is not JSON.")
    result = json.loads(raw[start:end + 1]).get("translations")
    if not isinstance(result, list) or len(result) != len(rows) or any(not str(x).strip() for x in result):
        raise ValueError("Translation response count mismatch or empty caption.")
    return [str(value).strip() for value in result]


def translate_avalai(rows, base, key, model):
    content = AvalAIClient(api_key=key, base_url=base).chat_completion(
        model,
        [{"role": "system", "content": "Translate English subtitles into concise, natural Persian. Return valid JSON only."},
         {"role": "user", "content": prompt_for(rows)}],
        temperature=0.15, max_tokens=5000, response_format={"type": "json_object"})
    return parse_translations(content, rows)


def translate_openai_compatible(rows, base, key, model):
    payload = {"model": model,
               "messages": [{"role": "system", "content": "Translate English subtitles into concise, natural Persian. Return valid JSON only."},
                            {"role": "user", "content": prompt_for(rows)}],
               "temperature": 0.15, "max_tokens": 5000,
               "response_format": {"type": "json_object"}}
    request = urllib.request.Request(base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(request, timeout=90) as response:
        data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Free provider returned no chat completion choices.")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "\\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return parse_translations(str(content), rows)


def translate_gemini(rows, key, model):
    payload = {"contents": [{"parts": [{"text": prompt_for(rows)}]}],
               "generationConfig": {"temperature": 0.15, "responseMimeType": "application/json"}}
    req = urllib.request.Request(f"{API}/{model}:generateContent?key={key}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as response:
        data = json.loads(response.read().decode("utf-8"))
    raw = "\n".join(part.get("text", "") for part in
                     data.get("candidates", [{}])[0].get("content", {}).get("parts", []))
    return parse_translations(raw, rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="subtitles.fa.srt")
    parser.add_argument("--model", default=os.getenv("SEO_GEMINI_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--batch-size", type=int, default=30)
    args = parser.parse_args()
    rows = parse_srt(Path(args.input).read_text(encoding="utf-8-sig"))
    if not rows:
        raise SystemExit("No subtitle entries found.")
    batch_size = max(1, min(args.batch_size, 50))
    provider_routes = []
    avalai_key = os.getenv("AVALAI_API_KEY", "").strip()
    avalai_base = os.getenv("AVALAI_BASE_URL", "https://api.avalai.ir/v1").strip()
    if avalai_key:
        try:
            models = discover_free_models(avalai_base, avalai_key, task="translation",
                                          preferred=os.getenv("AVALAI_MODEL", "auto"))
            provider_routes.extend((\"AvalAI\", avalai_base, avalai_key, model) for model in models)
        except Exception as exc:
            print("AVALAI_DISCOVERY_FAILED; continuing to existing free fallback: " + type(exc).__name__, file=sys.stderr)
    free_base = os.getenv("FREELLMAPI_BASE_URL", "").strip()
    free_key = os.getenv("FREELLMAPI_API_KEY", "").strip()
    if free_base and free_key:
        try:
            provider_routes.extend(("FreeLLMAPI", free_base, free_key, model) for model in
                discover_free_models(free_base, free_key, task="translation",
                                     preferred=os.getenv("FREELLMAPI_MODEL", "auto")))
        except Exception as exc:
            print("FREELLMAPI_DISCOVERY_FAILED: " + type(exc).__name__, file=sys.stderr)
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        try:
            provider_routes.extend(("OpenRouter", "https://openrouter.ai/api/v1", openrouter_key, model) for model in
                discover_free_models("https://openrouter.ai/api/v1", openrouter_key, task="translation",
                                     preferred=os.getenv("OPENROUTER_MODEL", "auto")))
        except Exception as exc:
            print("OPENROUTER_DISCOVERY_FAILED: " + type(exc).__name__, file=sys.stderr)
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    translated = []
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        values = None
        for provider, base, key, model in provider_routes:
            try:
                if provider == "AvalAI":
                    values = translate_avalai(batch, base, key, model)
                else:
                    values = translate_openai_compatible(batch, base, key, model)
                print(f"SUBTITLE_PROVIDER={provider} model={model}")
                break
            except Exception as exc:
                print(f"{provider.upper()}_SUBTITLE_ROUTE_FAILED model={model} error={type(exc).__name__}", file=sys.stderr)
        if values is None and gemini_key:
            values = translate_gemini(batch, gemini_key, args.model)
            print(f"SUBTITLE_PROVIDER=GEMINI model={args.model}")
        if values is None:
            raise RuntimeError("No explicitly free AvalAI, FreeLLMAPI or OpenRouter model was available and GEMINI_API_KEY fallback is not configured.")
        translated.extend({**row, "text": value} for row, value in zip(batch, values))
        print(f"Translated {len(translated)}/{len(rows)} subtitle cues.")
        time.sleep(0.2)
    output = "\n\n".join(f"{row['index']}\n{row['time']}\n{row['text']}" for row in translated) + "\n"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(output, encoding="utf-8")
    print(f"PERSIAN_SRT_CREATED {args.output}; cue count and timestamps preserved.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("SRT translation failed: " + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
