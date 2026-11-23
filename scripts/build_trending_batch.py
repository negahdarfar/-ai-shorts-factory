#!/usr/bin/env python3
"""Select distinct current Google Trends topics and create an MPT batch manifest."""
import argparse
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from topic_history import load_seen_topics, load_published_topics

RSS = "https://trends.google.com/trending/rss?geo={geo}"
FALLBACK = [
    "The science behind why the Moon appears larger near the horizon",
    "The surprising survival strategy of tardigrades",
    "How deep-sea animals create their own light",
    "The mystery of how ancient Roman concrete lasted so long",
    "Why humans experience déjà vu",
    "How the James Webb Space Telescope detects distant planets",
    "The hidden physics behind a rainbow",
    "Why octopuses have three hearts",
]
PROMPT = (
    "Create an original, highly engaging English YouTube Short for a general audience. "
    "Open with a specific curiosity hook in the first 1-2 seconds. Keep the script concise "
    "for a 60-120 second video. Explain one clear idea, build curiosity, deliver a "
    "satisfying payoff, and finish naturally. Use accurate, checkable facts; never invent "
    "statistics, quotes, dates, or sources. If a claim is uncertain, qualify it or omit it. "
    "VISUAL MATCHING IS CRITICAL: write narration in short, concrete sentences that can each "
    "be illustrated by an obvious real-world shot. For every sentence, make the visual subject "
    "and action unmistakable using literal stock-footage search terms (specific object, place, "
    "person, process, or action). Keep every shot directly relevant to the exact sentence being "
    "spoken. Prefer close-ups, demonstrations, diagrams, landmarks, and authentic topic-specific "
    "footage over generic scenery, random people, unrelated city shots, or decorative b-roll. "
    "Do not repeat the same visual idea or recycle a generic establishing shot. If a topic is "
    "abstract, explain it through a concrete example or a clearly named scientific process. "
    "Avoid vague pronouns, filler transitions, repeated phrases, generic introductions, and "
    "clickbait claims the video does not support."
)

def clean(value):
    return re.sub(r"\s+", " ", (value or "").strip())

def load_trends(geo):
    request = urllib.request.Request(
        RSS.format(geo=geo),
        headers={"User-Agent": "Mozilla/5.0 (compatible; ShortsFactory/1.0)"}
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        root = ET.fromstring(response.read())
    items = []
    for node in root.findall(".//item"):
        title = clean(node.findtext("title"))
        if title and title not in items:
            items.append(title)
    return items

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--geo", default="US")
    parser.add_argument("--state-dir", default="mpt-state")
    parser.add_argument("--output", default="trending_batch.json")
    args = parser.parse_args()
    count = max(1, min(4, args.count))
    state_dir = Path(args.state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        seen = load_seen_topics(state_dir) | load_published_topics(state_dir)
    except RuntimeError as exc:
        raise SystemExit(str(exc))

    try:
        topics = load_trends(args.geo)
        print(f"Loaded {len(topics)} current Google Trends topics for {args.geo}.")
    except Exception as exc:
        print(f"Google Trends feed unavailable ({exc}); using the curated fallback list.")
        topics = []

    fresh = [t for t in topics if t.lower() not in {x.lower() for x in seen}]
    if len(fresh) < count:
        fresh.extend(t for t in FALLBACK if t.lower() not in {x.lower() for x in seen | set(fresh)})
    chosen = fresh[:count]
    if len(chosen) < count:
        raise SystemExit(f"Could only find {len(chosen)} non-repeated topics; refusing to duplicate videos.")

    batch = []
    for topic in chosen:
        batch.append({
            "video_subject": topic,
            "video_language": "en-US",
            "video_aspect": "9:16",
            "video_count": 1,
            "video_script_prompt": PROMPT
        })

    Path(args.output).write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    selected_file = Path("selected_trends.json")
    selected_file.write_text(json.dumps({
        "geo": args.geo,
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "topics": chosen
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    seen.update(chosen)
    seen_file = state_dir / "seen_topics.json"
    seen_file.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=2), encoding="utf-8")
    for index, topic in enumerate(chosen, 1):
        print(f"{index}. {topic}")
    print(f"Wrote {args.output}")

if __name__ == "__main__":
    main()
