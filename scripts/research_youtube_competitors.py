#!/usr/bin/env python3
"""Research recent YouTube videos competing for each planned topic.

Uses YouTube Data API v3 with an API key. This is a lightweight public-video
benchmark, NOT keyword search volume, private channel analytics, or a ranking predictor.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://www.googleapis.com/youtube/v3"


def api_get(resource, params, api_key):
    query = dict(params)
    query["key"] = api_key
    url = f"{API}/{resource}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "YouTubeCompetitorResearch/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"YouTube Data API request failed for {resource}: {exc}") from exc


def clean(value, limit=250):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def research_topic(topic, api_key, days, max_results):
    published_after = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")

    search = api_get("search", {
        "part": "snippet",
        "type": "video",
        "q": topic,
        "order": "viewCount",
        "publishedAfter": published_after,
        "maxResults": max_results,
        "videoDuration": "short",
        "safeSearch": "moderate",
    }, api_key)

    ids = [
        item.get("id", {}).get("videoId")
        for item in search.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    if not ids:
        return {
            "query": topic, "window_days": days, "videos_found": 0,
            "competitors": [], "insight": "No matching recent Shorts returned by the API."
        }

    details = api_get("videos", {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(ids),
        "maxResults": len(ids),
    }, api_key)

    competitors = []
    now = datetime.now(timezone.utc)
    for item in details.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        published = snippet.get("publishedAt")
        try:
            age_days = max(
                0.25,
                (now - datetime.fromisoformat(published.replace("Z", "+00:00"))).total_seconds() / 86400
            )
        except Exception:
            age_days = None
        views = int(stats.get("viewCount", 0) or 0)
        likes = int(stats.get("likeCount", 0) or 0)
        comments = int(stats.get("commentCount", 0) or 0)
        title = clean(snippet.get("title"), 180)
        competitors.append({
            "video_id": item.get("id"),
            "title": title,
            "channel_title": clean(snippet.get("channelTitle"), 120),
            "published_at": published,
            "views": views,
            "likes": likes,
            "comments": comments,
            "views_per_day_estimate": round(views / age_days, 1) if age_days else None,
            "likes_per_view": round(likes / views, 4) if views else 0,
            "comments_per_view": round(comments / views, 4) if views else 0,
            "title_length": len(title),
            "title_hook_pattern": (
                "question" if "?" in title else
                "number" if re.search(r"\\d", title) else
                "how_why" if re.match(r"(?i)^(how|why|what|when|where)\\b", title) else
                "curiosity_or_statement"
            ),
            "url": f"https://www.youtube.com/watch?v={item.get('id')}",
        })

    # Views/day surfaces newer breakouts instead of only older high-view uploads.
    competitors.sort(key=lambda x: (x["views_per_day_estimate"] or 0, x["views"]), reverse=True)
    view_values = [x["views"] for x in competitors]
    avg_views = round(sum(view_values) / len(view_values)) if view_values else 0
    top = competitors[:5]
    patterns = {}
    for row in competitors:
        pattern = row["title_hook_pattern"]
        patterns[pattern] = patterns.get(pattern, 0) + 1
    strongest = top[0] if top else None
    return {
        "query": topic,
        "window_days": days,
        "videos_found": len(competitors),
        "average_views_in_sample": avg_views,
        "top_competitors": top,
        "title_hook_pattern_counts": patterns,
        "top_breakout_signal": {
            "title": strongest["title"],
            "views_per_day_estimate": strongest["views_per_day_estimate"],
            "title_hook_pattern": strongest["title_hook_pattern"],
            "url": strongest["url"],
        } if strongest else None,
        "sample_note": "Recent Shorts sample ranked primarily by estimated views per day; this is a directional public-data signal, not proof of virality or a complete market sample.",
        "insight": (
            "Use breakout titles and engagement only to infer broad audience-interest patterns. "
            "Create a new factual angle, original script, and independently sourced visuals; never copy competitor wording or footage."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="trending_batch.json")
    parser.add_argument("--output", default="youtube_competitor_research.json")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-results", type=int, default=10)
    args = parser.parse_args()

    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY is required for public competitor research.")

    topics = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(topics, list) or not topics:
        raise SystemExit("Input must be a non-empty list of video topics.")

    reports = []
    for index, item in enumerate(topics, 1):
        topic = clean(item.get("video_subject") if isinstance(item, dict) else "")
        if not topic:
            raise SystemExit(f"Topic item {index} has no video_subject.")
        print(f"Researching recent YouTube Shorts {index}/{len(topics)}: {topic}")
        reports.append(research_topic(
            topic, api_key, max(1, min(args.days, 365)),
            max(1, min(args.max_results, 25))
        ))

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "YouTube Data API v3 search.list + videos.list",
        "limitations": [
            "No keyword search-volume or keyword-difficulty data is provided.",
            "Search results are a partial sample and are not a complete competitor census.",
            "Public view counts do not reveal CTR, retention, watch time, or private channel analytics.",
            "Results do not guarantee ranking or future performance."
        ],
        "topics": reports,
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote competitor research for {len(reports)} topics to {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"Competitor research failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
