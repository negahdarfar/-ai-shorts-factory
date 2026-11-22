#!/usr/bin/env python3
"""Export NexLev's validated AI scripts to Automated Video Generator jobs.

This is a format adapter only: it never generates fallback scripts, downloads
media, invokes an LLM, or publishes videos.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def _slug(value):
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value)).strip("_").lower()
    return slug[:64] or "nexlev_short"


def _split_sentences(script):
    parts = re.split(r"(?<=[.!?])\s+", script.strip())
    return [part.strip() for part in parts if part.strip()]


def _with_visual_directions(script, terms):
    sentences = _split_sentences(script)
    if not sentences:
        raise ValueError("video_script must contain readable sentences.")
    groups = [[] for _ in terms]
    for index, sentence in enumerate(sentences):
        bucket = min(len(terms) - 1, index * len(terms) // len(sentences))
        groups[bucket].append(sentence)
    blocks = []
    for term, group in zip(terms, groups):
        if group:
            blocks.append(f"[Visual: {term}]\n{' '.join(group)}")
    return "\n\n".join(blocks)


def build_jobs(records, expected_count=4):
    if not isinstance(records, list) or len(records) != expected_count:
        raise ValueError(f"Expected exactly {expected_count} content records.")
    jobs = []
    seen_topics = set()
    seen_ids = set()
    for index, row in enumerate(records, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Record {index} must be an object.")
        topic = str(row.get("topic", "")).strip()
        if not topic:
            raise ValueError(f"Record {index} is missing topic.")
        topic_key = topic.casefold()
        if topic_key in seen_topics:
            raise ValueError(f"Duplicate topic at record {index}: {topic}")
        seen_topics.add(topic_key)

        source = str(row.get("content_source", "")).strip()
        if not source or source == "local_template_fallback":
            raise ValueError(
                f"Record {index} is not approved AI content (content_source={source or 'missing'}). "
                "Local template drafts are not eligible for rendering or publication."
            )

        script = str(row.get("video_script", "")).strip()
        word_count = len(script.split())
        if not 120 <= word_count <= 145:
            raise ValueError(
                f"Record {index} script must contain 120-145 words; found {word_count}."
            )
        metadata = row.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError(f"Record {index} is missing SEO metadata.")
        title = str(metadata.get("title", "")).strip()
        if not title:
            raise ValueError(f"Record {index} is missing metadata.title.")

        terms = row.get("video_terms")
        if not isinstance(terms, list):
            raise ValueError(f"Record {index} video_terms must be a list.")
        terms = list(dict.fromkeys(str(term).strip() for term in terms if str(term).strip()))
        if not 5 <= len(terms) <= 8:
            raise ValueError(f"Record {index} needs 5-8 distinct visual search terms.")
        if any(len(term.split()) < 2 for term in terms):
            raise ValueError(f"Record {index} contains a vague one-word visual term.")

        job_id = _slug(f"nexlev_{index}_{topic}")
        if job_id in seen_ids:
            raise ValueError(f"Generated duplicate job id: {job_id}")
        seen_ids.add(job_id)
        jobs.append({
            "id": job_id,
            "title": title[:100],
            "orientation": "portrait",
            "language": "english",
            "showText": True,
            "script": _with_visual_directions(script, terms),
        })
    return jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="seo_metadata.json")
    parser.add_argument("--output", default="avgen-input-scripts.json")
    parser.add_argument("--expected-count", type=int, default=4)
    args = parser.parse_args()
    if args.expected_count < 1 or args.expected_count > 20:
        parser.error("--expected-count must be between 1 and 20")
    try:
        records = json.loads(Path(args.input).read_text(encoding="utf-8"))
        jobs = build_jobs(records, args.expected_count)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"AVGEN_MANIFEST_READY: {len(jobs)} AI-authored vertical jobs -> {output}")
        print("No LLM call, media download, render, upload, or publication was performed.")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"AVGEN_EXPORT_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
