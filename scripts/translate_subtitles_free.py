#!/usr/bin/env python3
"""Translate generated SRT captions into Persian using explicitly free LLM routes."""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from free_model_router import discover_free_models
from avalai_client import AvalAIClient

BLOCK = re.compile(r"^\s*(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3})\s*\n([\s\S]*?)\s*$")


def parse_srt(text):
    rows = []
    for block in re.split(r"\n\s*\n", text.strip()):
        match = BLOCK.match(block.strip())
        if not match:
            raise ValueError("Malformed SRT block.")
        rows.append({"index": int(match.group(1)), "time": match.group(2),
                     "text": re.sub(r"\s+", " ", match.group(3)).strip()})
    if not rows:
        raise ValueError("No subtitle cues found.")
    return rows


def translate_batch(rows, base, key, model):
    prompt = (
        "Translate the following English subtitle captions into natural, concise Persian (Farsi). "
        "Keep meaning, names, numbers, and tone. Use fluent readable Persian. Do not add explanations. "
        "Return only JSON with one key translations containing exactly one string per input caption. "
        "Do not merge, split, omit, or reorder captions.\n"
        + json.dumps([row["text"] for row in rows], ensure_ascii=False)
    )
    payload = {"model": model, "messages": [
        {"role": "system", "content": "You are a professional English-to-Persian subtitle translator. Output valid JSON only."},
        {"role": "user", "content": prompt}],
        "temperature": 0.1, "max_tokens": 5000, "response_format": {"type": "json_object"}}
    if base.rstrip("/") == os.getenv("AVALAI_BASE_URL", "https://api.avalai.ir/v1").rstrip("/") or base.rstrip("/") in ("https://api.avalai.ir/v1", "https://api.avalapis.ir/v1", "https://api.avalai.org/v1"):
        content = AvalAIClient(api_key=key, base_url=base).chat_completion(
            model, payload["messages"], temperature=0.1, max_tokens=5000,
            response_format={"type": "json_object"})
        data = {"choices": [{"message": {"content": content}}]}
    else:
        request = urllib.request.Request(base.rstrip("/") + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Translation model returned no choices.")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
    content = str(content).strip()
    fence = chr(96) * 3
    if content.startswith(fence):
        content = content[len(fence):]
        if content.lower().startswith("json"):
            content = content[4:]
        if content.rstrip().endswith(fence):
            content = content.rstrip()[:-len(fence)]
    first, last = content.find("{"), content.rfind("}")
    if first < 0 or last <= first:
        raise ValueError("Translation response is not JSON.")
    translations = json.loads(content[first:last + 1]).get("translations")
    if not isinstance(translations, list) or len(translations) != len(rows):
        raise ValueError("Translation count does not match input cues.")
    result = [str(value).strip() for value in translations]
    if any(not value for value in result):
        raise ValueError("Translation contains an empty caption.")
    return result


def configured_routes():
    result = []
    base, key = os.getenv("FREELLMAPI_BASE_URL", "").strip(), os.getenv("FREELLMAPI_API_KEY", "").strip()
    if base and key:
        try:
            result += [(base, key, model) for model in discover_free_models(
                base, key, task="translation", preferred=os.getenv("FREELLMAPI_MODEL", "auto"))]
        except Exception as exc:
            print("FreeLLMAPI translation discovery failed:", type(exc).__name__, file=sys.stderr)
    avalai_key = os.getenv("AVALAI_API_KEY", "").strip()
    if avalai_key:
        base = os.getenv("AVALAI_BASE_URL", "https://api.avalai.ir/v1").strip()
        try:
            result += [(base, avalai_key, model) for model in discover_free_models(
                base, avalai_key, task="translation", preferred=os.getenv("AVALAI_MODEL", "auto"))]
        except Exception as exc:
            print("AvalAI translation discovery failed:", type(exc).__name__, file=sys.stderr)
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if key:
        base = "https://openrouter.ai/api/v1"
        try:
            result += [(base, key, model) for model in discover_free_models(
                base, key, task="translation", preferred=os.getenv("OPENROUTER_MODEL", "auto"))]
        except Exception as exc:
            print("OpenRouter translation discovery failed:", type(exc).__name__, file=sys.stderr)
    return result


def translate_file(source, output, batch_size=20):
    rows = parse_srt(Path(source).read_text(encoding="utf-8-sig"))
    routes = configured_routes()
    if not routes:
        raise RuntimeError("No explicitly free translation model was discovered.")
    translated = []
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        last_error = None
        for base, key, model in routes:
            try:
                values = translate_batch(batch, base, key, model)
                translated.extend({**row, "text": value} for row, value in zip(batch, values))
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                print(f"TRANSLATION_ATTEMPT_FAILED model={model} error={type(exc).__name__}", file=sys.stderr)
        if last_error:
            raise RuntimeError(f"All free models failed on subtitle batch {start // batch_size + 1}.") from last_error
        print(f"TRANSLATED_CUES {len(translated)}/{len(rows)}")
        time.sleep(0.15)
    output_text = "\n\n".join(
        f"{row['index']}\n{row['time']}\n{row['text']}" for row in translated
    ) + "\n"
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(output_text, encoding="utf-8")
    return len(translated)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="longform-output/narration.fa.srt")
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 40:
        raise SystemExit("Batch size must be 1-40.")
    count = translate_file(args.input, args.output, args.batch_size)
    print(f"PERSIAN_SUBTITLES_READY cues={count} output={args.output}")


if __name__ == "__main__":
    main()
