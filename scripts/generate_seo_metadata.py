#!/usr/bin/env python3
"""Generate fact-safe YouTube Shorts SEO drafts with Gemini and optional competitor context."""
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
DEFAULT_MODEL = "gemini-3.8-flash"


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


def request_metadata(topic, language, model, api_key, competitor_context=None):
    context = json.dumps(competitor_context or {}, ensure_ascii=False)[:5000]
    prompt = f"""
You are a meticulous YouTube Shorts SEO editor. Audience/language: {language}.
Topic: {topic}
Recent public competitor sample (partial; never copy): {context}
Use competitor context only to find a distinct content angle. Do not infer keyword volume,
CTR, retention, or causal ranking factors from public view counts.

Return ONLY valid JSON with exactly these keys:
{{
  "primary_keyword": "one natural search phrase",
  "secondary_keywords": ["3 to 6 relevant phrases"],
  "title": "compelling accurate title, ideally 45-65 characters",
  "description": "2-4 concise useful sentences; use primary phrase naturally",
  "hashtags": ["up to 3 directly relevant hashtags"],
  "tags": ["8-15 concise relevant YouTube tags"],
  "pinned_comment": "one useful question inviting genuine discussion",
  "thumbnail_concept": "one clear visual idea with 2-4 optional overlay words",
  "search_intent": "what a viewer is likely trying to learn"
}}
Rules: no fabricated facts, stats, events or quotes; no misleading clickbait, keyword stuffing,
irrelevant trending terms or copied competitor wording. Metadata must accurately represent
the topic; it is a preproduction draft and must be checked against the final video.
This is a Short: do not create chapters or timestamps. Keep metadata in {language}.
"""
    url = f"{API_ROOT}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "YouTubeSEOFactory/1.0"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1500]
        raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail}") from exc

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    result = extract_json("\n".join(p.get("text", "") for p in parts))
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
    result["tags"] = list(dict.fromkeys(
        clean_text(x, 60) for x in result["tags"][:15] if clean_text(x)
    ))
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
    parser.add_argument("--research", default="youtube_competitor_research.json")
    parser.add_argument("--language", default="English")
    parser.add_argument("--model", default=os.getenv("SEO_GEMINI_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required to generate SEO metadata.")
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(source, list) or not source:
        raise SystemExit("Input must be a non-empty list of video topics.")

    try:
        research_data = json.loads(Path(args.research).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        research_data = {}
    research_by_topic = {
        clean_text(item.get("query")).lower(): item
        for item in research_data.get("topics", [])
        if isinstance(item, dict)
    } if isinstance(research_data, dict) else {}

    output = []
    for index, item in enumerate(source, 1):
        topic = clean_text(item.get("video_subject") if isinstance(item, dict) else "")
        if not topic:
            raise SystemExit(f"Input item {index} has no video_subject.")
        print(f"Generating SEO metadata {index}/{len(source)}: {topic}")
        metadata = request_metadata(
            topic, args.language, args.model, api_key, research_by_topic.get(topic.lower())
        )
        output.append({
            "index": index, "topic": topic, "language": args.language,
            "metadata": metadata,
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "basis": "topic_and_optional_public_competitor_sample",
            "requires_final_script_review": True
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
