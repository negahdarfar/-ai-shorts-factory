#!/usr/bin/env python3
"""Validate generated YouTube SEO metadata before it becomes an upload manifest."""
import argparse
import json
import re
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="seo_metadata.json")
    parser.add_argument("--expected-count", type=int, default=4)
    args = parser.parse_args()

    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != args.expected_count:
        raise SystemExit(
            f"Expected {args.expected_count} SEO records; got "
            f"{len(records) if isinstance(records, list) else 'non-list'}."
        )

    errors = []
    seen_topics = set()
    for index, record in enumerate(records, 1):
        topic = str(record.get("topic", "")).strip()
        meta = record.get("metadata", {})
        if not topic:
            errors.append(f"Item {index}: missing topic.")
        if topic.lower() in seen_topics:
            errors.append(f"Item {index}: duplicate topic.")
        seen_topics.add(topic.lower())

        title = str(meta.get("title", "")).strip()
        description = str(meta.get("description", "")).strip()
        primary = str(meta.get("primary_keyword", "")).strip()
        tags = meta.get("tags", [])
        hashtags = meta.get("hashtags", [])

        if not title:
            errors.append(f"Item {index}: missing title.")
        elif len(title) > 100:
            errors.append(f"Item {index}: title exceeds YouTube's 100-character limit.")
        if not description:
            errors.append(f"Item {index}: missing description.")
        elif len(description) > 5000:
            errors.append(f"Item {index}: description exceeds 5000 characters.")
        if not primary:
            errors.append(f"Item {index}: missing primary keyword.")
        elif primary.lower() not in (title + " " + description).lower():
            errors.append(f"Item {index}: primary keyword is absent from title and description.")
        if not isinstance(tags, list) or len(tags) > 15:
            errors.append(f"Item {index}: tags must be a list of at most 15 entries.")
        elif len({str(x).strip().lower() for x in tags}) != len(tags):
            errors.append(f"Item {index}: duplicate tags.")
        if not isinstance(hashtags, list) or len(hashtags) > 3:
            errors.append(f"Item {index}: hashtags must be a list of at most 3 entries.")
        elif any(not re.fullmatch(r"[A-Za-z0-9_]+", str(x).lstrip("#")) for x in hashtags):
            errors.append(f"Item {index}: hashtag contains unsupported characters.")

    if errors:
        for error in errors:
            print("SEO_VALIDATION_ERROR: " + error, file=sys.stderr)
        raise SystemExit(1)

    print(f"SEO_METADATA_VALIDATION_PASSED: {len(records)} records.")
    print("Reminder: human review against the final video script is still required.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError) as exc:
        print(f"SEO validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
