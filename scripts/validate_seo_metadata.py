#!/usr/bin/env python3
"""Strict validation for YouTube SEO/content manifests before production or publishing."""
import argparse
import json
import re
import sys
from pathlib import Path

def tokens(value):
    return {x.casefold() for x in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", str(value or "")) if len(x) > 2}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="seo_metadata.json")
    parser.add_argument("--expected-count", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.expected_count <= 10:
        raise SystemExit("--expected-count must be between 1 and 10.")
    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} SEO records; got {len(records) if isinstance(records, list) else 'non-list'}.")
    errors, seen_topics, seen_titles = [], set(), set()
    generic_phrases = {"interesting facts", "quick facts", "things you didn't know", "explained"}
    for index, record in enumerate(records, 1):
        topic = str(record.get("topic", "")).strip()
        meta = record.get("metadata", {}) if isinstance(record, dict) else {}
        if not topic: errors.append(f"Item {index}: missing topic.")
        if topic.casefold() in seen_topics: errors.append(f"Item {index}: duplicate topic.")
        seen_topics.add(topic.casefold())
        approved_sources = {"gemini_batch", "gemini_free_batch", "freellmapi_batch", "cloudflare_batch", "openrouter_batch"}
        metadata_source = record.get("metadata_source")
        content_source = record.get("content_source")
        if metadata_source not in approved_sources or content_source not in approved_sources or metadata_source != content_source:
            errors.append(f"Item {index}: content must come from one approved AI batch provider (Gemini Free Tier, verified-free FreeLLMAPI/OpenRouter, or the pinned free Cloudflare Workers AI model); local templates and mixed providers are blocked.")
        title = str(meta.get("title", "")).strip()
        description = str(meta.get("description", "")).strip()
        primary = str(meta.get("primary_keyword", "")).strip()
        tags, hashtags = meta.get("tags", []), meta.get("hashtags", [])
        script = str(record.get("video_script", "")).strip()
        video_terms = record.get("video_terms", [])
        if not 155 <= len(script.split()) <= 270: errors.append(f"Item {index}: narration script must contain 155-270 words for a 60-120 second Short.")
        if any(p in script.casefold() for p in ("let's take a closer look", "what does this subject actually mean", "look beyond the headline")):
            errors.append(f"Item {index}: generic placeholder narration detected.")
        if not isinstance(video_terms, list) or not 5 <= len(video_terms) <= 8 or any(not str(x).strip() for x in video_terms):
            errors.append(f"Item {index}: video_terms must contain 5-8 non-empty stock-footage search phrases.")
        if not title or len(title) > 100: errors.append(f"Item {index}: title is missing or exceeds 100 characters.")
        if title.casefold() in seen_titles: errors.append(f"Item {index}: duplicate title.")
        seen_titles.add(title.casefold())
        if any(p in title.casefold() for p in generic_phrases): errors.append(f"Item {index}: generic/non-distinctive title.")
        topic_words, title_words = tokens(topic), tokens(title)
        if topic_words and not (topic_words & title_words): errors.append(f"Item {index}: title does not visibly match the topic.")
        if not description or len(description) > 5000: errors.append(f"Item {index}: description is missing or exceeds 5000 characters.")
        if not primary or len(primary) < 3: errors.append(f"Item {index}: primary keyword is missing or too short.")
        elif primary.casefold() not in (title + " " + description).casefold(): errors.append(f"Item {index}: primary keyword is absent from title and description.")
        elif topic_words and len(topic_words & tokens(primary)) < max(1, (len(topic_words) + 1) // 2): errors.append(f"Item {index}: primary keyword is not sufficiently aligned with the actual topic.")
        if not isinstance(tags, list) or not 5 <= len(tags) <= 15: errors.append(f"Item {index}: tags must contain 5-15 relevant entries.")
        elif len({str(x).strip().casefold() for x in tags}) != len(tags): errors.append(f"Item {index}: duplicate tags.")
        if not isinstance(hashtags, list) or not 1 <= len(hashtags) <= 3: errors.append(f"Item {index}: hashtags must contain 1-3 entries.")
        elif any(not re.fullmatch(r"[A-Za-z0-9_]+", str(x).lstrip("#")) for x in hashtags): errors.append(f"Item {index}: hashtag contains unsupported characters.")
    if errors:
        for error in errors: print("SEO_VALIDATION_ERROR: " + error, file=sys.stderr)
        raise SystemExit(1)
    print(f"SEO_METADATA_VALIDATION_PASSED: {len(records)} researched records; titles are unique and topic-aligned.")

if __name__ == "__main__":
    try: main()
    except (OSError, ValueError, TypeError) as exc:
        print(f"SEO validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
