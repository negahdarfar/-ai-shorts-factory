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

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
METRICS = (
    "views,engagedViews,estimatedMinutesWatched,averageViewDuration,"
    "averageViewPercentage,likes,comments,shares,subscribersGained"
)
VIDEO_BATCH_SIZE = 100


def shorts_only(result):
    """Keep only Shorts rows when creatorContentType is returned."""
    headers = [item.get("name") for item in result.get("columnHeaders", [])]
    if "creatorContentType" not in headers:
        return {"columnHeaders": result.get("columnHeaders", []), "rows": [],
                "unavailable": "creatorContentType was not returned; refusing to mix Shorts with other formats."}
    index = headers.index("creatorContentType")
    rows = [row for row in (result.get("rows") or []) if len(row) > index and row[index] == "SHORTS"]
    return {"columnHeaders": result.get("columnHeaders", []), "rows": rows}


def add_engagement_proxy(report):
    """Add an explicitly labelled engagedViews/views proxy; not the Studio swipe metric."""
    headers = [item.get("name") for item in report.get("columnHeaders", [])]
    if "views" not in headers or "engagedViews" not in headers:
        return report
    view_index = headers.index("views")
    engaged_index = headers.index("engagedViews")
    records = []
    for row in report.get("rows") or []:
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


def load_factory_video_ids(path: Path, start: date, end: date):
    """Return completed public Shorts uploaded by this factory in the report window."""
    if not path.is_file():
        return [], "The durable upload ledger is not present."
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [], f"The durable upload ledger could not be read: {exc}"
    uploads = ledger.get("uploads") if isinstance(ledger, dict) else None
    if not isinstance(uploads, dict):
        return [], "The durable upload ledger has an invalid structure."
    ids = []
    seen = set()
    for entry in uploads.values():
        if not isinstance(entry, dict) or entry.get("mode") != "public" or entry.get("status") != "completed":
            continue
        result = entry.get("result") if isinstance(entry.get("result"), dict) else {}
        video_id = str(entry.get("video_id") or result.get("video_id") or "").strip()
        timestamp = str(entry.get("publish_at_utc") or entry.get("completed_at") or "")
        try:
            published_day = date.fromisoformat(timestamp[:10])
        except ValueError:
            continue
        if video_id and start <= published_day <= end and video_id not in seen:
            seen.add(video_id)
            ids.append(video_id)
    return ids, None


def query_video_rows(api, start, end, video_ids):
    """Query the channel's own published Shorts IDs in small batches, avoiding result truncation."""
    headers = None
    all_rows = []
    for offset in range(0, len(video_ids), VIDEO_BATCH_SIZE):
        batch = video_ids[offset:offset + VIDEO_BATCH_SIZE]
        query = {
            "ids": "channel==MINE",
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "metrics": METRICS,
            "filters": "video==" + ",".join(batch),
            "maxResults": 200,
        }
        if len(batch) > 1:
            query["dimensions"] = "video"
        result = api.reports().query(**query).execute()
        batch_headers = result.get("columnHeaders", [])
        batch_rows = result.get("rows") or []
        if len(batch) == 1:
            video_header = {"name": "video", "dataType": "STRING", "columnType": "DIMENSION"}
            if not headers or headers[0].get("name") != "video":
                headers = [video_header] + (batch_headers or headers or [])
            all_rows.extend([[batch[0]] + row for row in batch_rows])
        else:
            headers = batch_headers or headers
            all_rows.extend(batch_rows)
    if headers is None:
        headers = [{"name": "video", "dataType": "STRING", "columnType": "DIMENSION"}]
    return {"columnHeaders": headers, "rows": all_rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--output", default="youtube_analytics.json")
    parser.add_argument("--upload-history", default="data/factory_state/upload_history.json")
    args = parser.parse_args()
    if not 1 <= args.days <= 90:
        raise SystemExit("--days must be from 1 to 90.")

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
        scopes=SCOPES,
    )
    try:
        credentials.refresh(Request())
    except Exception as exc:
        raise SystemExit(
            "Analytics OAuth refresh failed. Create YOUTUBE_ANALYTICS_REFRESH_TOKEN "
            "with the youtube.readonly and yt-analytics.readonly scopes; do not replace the working upload token. "
            + str(exc)
        ) from exc

    api = build("youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False)
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=args.days - 1)
    reports = {}

    try:
        daily_result = api.reports().query(
            ids="channel==MINE",
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            metrics=METRICS,
            dimensions="day,creatorContentType",
            sort="day",
            maxResults=200,
        ).execute()
        reports["shorts_daily"] = add_engagement_proxy(shorts_only(daily_result))
    except HttpError as exc:
        reports["shorts_daily"] = {
            "unavailable": f"YouTube Analytics API HTTP {exc.resp.status}; "
                           "the Shorts daily report is not available for this channel."
        }

    video_ids, ledger_warning = load_factory_video_ids(Path(args.upload_history), start, end)
    if ledger_warning:
        reports["shorts_videos"] = {"unavailable": ledger_warning}
    else:
        try:
            video_result = query_video_rows(api, start, end, video_ids)
            reports["shorts_videos"] = add_engagement_proxy(video_result)
            reports["shorts_videos"]["factory_video_ids_queried"] = len(video_ids)
        except HttpError as exc:
            reports["shorts_videos"] = {
                "unavailable": f"YouTube Analytics API HTTP {exc.resp.status}; "
                               "the factory video-level report is not available."
            }

    blocked_reports = [name for name, value in reports.items() if value.get("unavailable")]
    payload = {
        "status": "BLOCKED" if blocked_reports else "completed",
        "reason": ("Shorts Analytics reports unavailable: " + ", ".join(blocked_reports)) if blocked_reports else None,
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
        "scopes": SCOPES,
        "video_report_source": "Completed public video IDs in the durable factory upload ledger.",
        "note": "Shorts daily rows are filtered using creatorContentType=SHORTS. Video rows are restricted to factory-published public Shorts IDs. Data is delayed; the report ends three days before the run date."
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"YOUTUBE_SHORTS_ANALYTICS_SAVED {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Analytics failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
