#!/usr/bin/env python3
"""Fetch Shorts-specific YouTube Analytics using a dedicated read-only OAuth token."""
import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
METRICS = (
    "views,engagedViews,estimatedMinutesWatched,averageViewDuration,"
    "averageViewPercentage,likes,comments,shares,subscribersGained"
)


def shorts_only(result):
    """Keep only Shorts rows when creatorContentType is returned."""
    headers = [item.get("name") for item in result.get("columnHeaders", [])]
    if "creatorContentType" not in headers:
        return {"columnHeaders": result.get("columnHeaders", []), "rows": [],
                "unavailable": "creatorContentType was not returned; refusing to mix Shorts with other formats."}
    index = headers.index("creatorContentType")
    rows = [row for row in result.get("rows", []) if len(row) > index and row[index] == "SHORTS"]
    return {"columnHeaders": result.get("columnHeaders", []), "rows": rows}


def add_engagement_proxy(report):
    """Add an explicitly labelled engagedViews/views proxy; not the Studio swipe metric."""
    headers = [item.get("name") for item in report.get("columnHeaders", [])]
    if "views" not in headers or "engagedViews" not in headers:
        return report
    view_index = headers.index("views")
    engaged_index = headers.index("engagedViews")
    records = []
    for row in report.get("rows", []):
        if len(row) <= max(view_index, engaged_index):
            continue
        views = float(row[view_index] or 0)
        engaged = float(row[engaged_index] or 0)
        records.append({
            "row": row,
            "engaged_views_over_views_percent": round(100 * engaged / views, 2) if views else None,
        })
    report["rows_with_engagement_proxy"] = records
    report["engagement_proxy_note"] = (
        "engagedViews divided by views is a directional proxy only; it is not the exact "
        "YouTube Studio 'Stayed to watch' / 'Viewed vs swiped away' metric."
    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--output", default="youtube_analytics.json")
    args = parser.parse_args()
    if not 1 <= args.days <= 365:
        raise SystemExit("--days must be from 1 to 365.")

    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_ANALYTICS_REFRESH_TOKEN")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        raise SystemExit("Missing environment variables: " + ", ".join(missing))

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_ANALYTICS_REFRESH_TOKEN"].strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"].strip(),
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"].strip(),
        scopes=[SCOPE],
    )
    try:
        credentials.refresh(Request())
    except Exception as exc:
        raise SystemExit(
            "Analytics OAuth refresh failed. Create YOUTUBE_ANALYTICS_REFRESH_TOKEN "
            "with the yt-analytics.readonly scope; do not replace the working upload token. "
            + str(exc)
        ) from exc

    api = build("youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False)
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=args.days - 1)
    reports = {}

    queries = {
        "shorts_daily": {"dimensions": "day,creatorContentType", "sort": "day"},
        "shorts_videos": {"dimensions": "video,creatorContentType", "sort": "-engagedViews"},
    }
    for name, query in queries.items():
        try:
            result = api.reports().query(
                ids="channel==MINE",
                startDate=start.isoformat(),
                endDate=end.isoformat(),
                metrics=METRICS,
                dimensions=query["dimensions"],
                sort=query["sort"],
                maxResults=200,
            ).execute()
            reports[name] = add_engagement_proxy(shorts_only(result))
        except HttpError as exc:
            reports[name] = {
                "unavailable": f"YouTube Analytics API HTTP {exc.resp.status}; "
                               "this report combination may not be available for this channel."
            }

    payload = {
        "status": "completed",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "reports": reports,
        "metric_notes": {
            "views": "YouTube public views count plays/replays from the first frame.",
            "engagedViews": "Use this alongside views for meaningful Shorts engagement analysis.",
            "stay_to_watch_proxy": "engagedViews/views is a proxy, not the exact Studio swipe metric.",
            "impressions": "Shorts-feed exposure is not represented here as ordinary thumbnail impressions."
        },
        "source": "YouTube Analytics API v2",
        "scope": SCOPE,
        "note": "Reports are Shorts-filtered using creatorContentType=SHORTS. Recent days may be delayed."
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"YOUTUBE_SHORTS_ANALYTICS_SAVED {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Analytics failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
