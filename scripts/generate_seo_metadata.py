#!/usr/bin/env python3
"""Create structured, fact-safe YouTube SEO metadata drafts with Gemini.

Input is the selected topic batch. Output is a per-video metadata manifest.
This is a metadata drafting stage, not a ranking guarantee or live competitor audit.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"


def clean_text(value, limit=None):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    return value[:limit] if limit else value


def extract_json(text):
    text = (text or "").strip()
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```\s*$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Gemini response did not contain a JSON object.")
    return json.loads(text[start:end + 1])


def request_metadata(topic, language, model, api_key):
    prompt = f"""
You are a meticulous YouTube Shorts SEO editor. Create metadata for one short-form
video based ONLY on the topic below. Audience/language: {language}.
Topic: {topic}

Return ONLY valid JSON with exactly these keys:
{{
  "primary_keyword": "one natural search phrase",
  "secondary_keywords": ["3 to 6 relevant phrases"],
  "title": "compelling accurate title, ideally 45-65 characters, never misleading",
  "description": "2-4 concise sentences; explain actual topic, include primary phrase naturally",
  "hashtags": ["3 relevant hashtags, no #Shorts unless contextually appropriate"],
  "tags": ["8-15 relevant YouTube tags, concise, no duplicates"],
  "pinned_comment": "one useful question inviting genuine discussion",
  "thumbnail_concept": "one clear visual idea with 2-4 optional overlay words",
  "search_intent": "what a viewer is likely trying to learn"
}}

Rules:
- Do not invent facts, numbers, events, quotes, or claims about what the unseen video contains.
- No keyword stuffing, irrelevant trending terms, deceptive clickbait, or repeated hashtags.
- Title must accurately represent the supplied topic and create curiosity.
- Description must be readable and useful, not a keyword dump.
- Tags must be directly relevant; tags are secondary to viewer satisfaction and the actual content.
- The video is a YouTube Short. Do not create chapters/timestamps for a Short.
- Keep all metadata in {language}; hashtags may use natural English terms.
"""
    url = f"{API_ROOT}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.35,
            "responseMimeType": "application/json"
        }
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "YouTubeSEOFactory/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1500]
        raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail}") from exc
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "\n".join(p.get("text", "") for p in parts)
    result = extract_json(text)

    required = ("primary_keyword", "secondary_keywords", "title", "description",
                "hashtags", "tags", "pinned_comment", "thumbnail_concept", "search_intent")
    missing = [key for key in required if key not in result]
    if missing:
        raise ValueError("SEO response missing fields: " + ", ".join(missing))

    result["primary_keyword"] = clean_text(result["primary_keyword"], 100)
    result["secondary_keywords"] = [clean_text(x, 100) for x in result["secondary_keywords"][:6]]
    result["title"] = clean_text(result["title"], 100)
    result["description"] = clean_text(result["description"], 5000)
    result["hashtags"] = [clean_text(x, 60).lstrip("#") for x in result["hashtags"][:3]]
    result["tags"] = list(dict.fromkeys(clean_text(x, 60) for x in result["tags"][:15] if clean_text(x)))
    result["pinned_comment"] = clean_text(result["pinned_comment"], 500)
    result["thumbnail_concept"] = clean_text(result["thumbnail_concept"], 400)
    result["search_intent"] = clean_text(result["search_intent"], 300)
    if not result["title"] or not result["description"] or not result["primary_keyword"]:
        raise ValueError("Gemini returned empty required SEO fields.")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="trending_batch.json")
    parser.add_argument("--output", default="seo_metadata.json")
    parser.add_argument("--language", default="English")
    parser.add_argument("--model", default=os.getenv("SEO_GEMINI_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required to generate SEO metadata.")

    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(source, list) or not source:
        raise SystemExit("Input must be a non-empty list of video topics.")

    output = []
    for index, item in enumerate(source, 1):
        topic = clean_text(item.get("video_subject") if isinstance(item, dict) else "")
        if not topic:
            raise SystemExit(f"Input item {index} has no video_subject.")
        print(f"Generating SEO metadata {index}/{len(source)}: {topic}")
        metadata = request_metadata(topic, args.language, args.model, api_key)
        output.append({
            "index": index,
            "topic": topic,
            "language": args.language,
            "metadata": metadata,
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "basis": "topic_only_preproduction_draft",
            "requires_final_script_review": True,
        })

    Path(args.output).write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(output)} SEO metadata drafts to {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"SEO metadata generation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
