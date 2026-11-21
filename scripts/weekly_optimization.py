#!/usr/bin/env python3
"""Create conservative topic- and hook-aware Shorts recommendations from Analytics exports."""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path


def as_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def records(report):
    headers = [item.get("name") for item in report.get("columnHeaders", [])]
    output = []
    for row in report.get("rows") or []:
        if len(row) != len(headers):
            continue
        output.append(dict(zip(headers, row)))
    return output


def total(rows, key):
    return sum(as_number(row.get(key)) for row in rows)


def load_upload_metadata(path):
    file_path = Path(path)
    if not file_path.is_file():
        return {}, "Upload ledger is not present in this checkout."
    try:
        ledger = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, f"Upload ledger could not be read: {exc}"
    uploads = ledger.get("uploads") if isinstance(ledger, dict) else None
    if not isinstance(uploads, dict):
        return {}, "Upload ledger has an invalid structure."
    metadata = {}
    for entry in uploads.values():
        if not isinstance(entry, dict) or entry.get("mode") != "public" or entry.get("status") != "completed":
            continue
        result = entry.get("result") if isinstance(entry.get("result"), dict) else {}
        video_id = str(entry.get("video_id") or result.get("video_id") or "").strip()
        if not video_id:
            continue
        metadata[video_id] = {
            "topic": entry.get("topic") or result.get("topic") or "",
            "title": entry.get("title") or result.get("title") or "",
            "hook_text": entry.get("hook_text") or result.get("hook_text") or "",
            "hook_type": entry.get("hook_type") or result.get("hook_type") or "unknown",
        }
    return metadata, None


def aggregate_groups(rows, key):
    grouped = {}
    for row in rows:
        label = str(row.get(key) or "").strip()
        if not label:
            continue
        item = grouped.setdefault(label, {
            key: label,
            "sample_count": 0,
            "views": 0.0,
            "engagedViews": 0.0,
            "likes": 0.0,
            "comments": 0.0,
            "shares": 0.0,
            "_weighted_view_percentage": 0.0,
            "_view_weight": 0.0,
        })
        views = as_number(row.get("views"))
        item["sample_count"] += 1
        item["views"] += views
        item["engagedViews"] += as_number(row.get("engagedViews"))
        item["likes"] += as_number(row.get("likes"))
        item["comments"] += as_number(row.get("comments"))
        item["shares"] += as_number(row.get("shares"))
        if row.get("averageViewPercentage") not in (None, ""):
            item["_weighted_view_percentage"] += as_number(row.get("averageViewPercentage")) * views
            item["_view_weight"] += views

    output = []
    for item in grouped.values():
        weight = item.pop("_view_weight")
        weighted = item.pop("_weighted_view_percentage")
        item["averageViewPercentage"] = round(weighted / weight, 2) if weight else None
        item["engaged_views_over_views_percent"] = (
            round(100 * item["engagedViews"] / item["views"], 2) if item["views"] else None
        )
        for name in ("views", "engagedViews", "likes", "comments", "shares"):
            item[name] = int(item[name])
        output.append(item)
    return sorted(output, key=lambda item: item["engagedViews"], reverse=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="youtube_analytics.json")
    parser.add_argument("--output", default="weekly_optimization.json")
    parser.add_argument("--markdown", default="weekly_optimization.md")
    parser.add_argument("--upload-history", default="data/factory_state/upload_history.json")
    args = parser.parse_args()

    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if source.get("status") != "completed":
        result = {
            "status": "BLOCKED",
            "reason": source.get("reason", "Shorts Analytics data is not available."),
            "recommendations": [],
        }
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        Path(args.markdown).write_text("# Weekly Shorts Optimization\n\n**BLOCKED:** " + result["reason"] + "\n", encoding="utf-8")
        print("WEEKLY_OPTIMIZATION_BLOCKED")
        return

    reports = source.get("reports", {})
    daily_report = reports.get("shorts_daily", {})
    video_report = reports.get("shorts_videos", {})
    daily = records(daily_report)
    videos = records(video_report)
    if not daily and not videos:
        result = {
            "status": "NO_DATA",
            "period": {"start": source.get("start_date"), "end": source.get("end_date")},
            "recommendations": ["Wait for Shorts analytics data, then rerun this report."],
        }
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        Path(args.markdown).write_text("# Weekly Shorts Optimization\n\nNo Shorts rows were returned for this period.\n", encoding="utf-8")
        print("WEEKLY_OPTIMIZATION_NO_DATA")
        return

    upload_metadata, metadata_warning = load_upload_metadata(args.upload_history)
    for row in videos:
        video_id = str(row.get("video", ""))
        row.update(upload_metadata.get(video_id, {}))
        row["engaged_views_over_views_percent"] = (
            round(100 * as_number(row.get("engagedViews")) / as_number(row.get("views")), 2)
            if as_number(row.get("views")) > 0 else None
        )
        row["video_url"] = "https://www.youtube.com/watch?v=" + video_id

    end = date.fromisoformat(source["end_date"])
    split = end - timedelta(days=13)
    recent = []
    previous = []
    for row in daily:
        try:
            day = date.fromisoformat(str(row.get("day")))
        except ValueError:
            continue
        (recent if day >= split else previous).append(row)

    recent_views = total(recent, "views")
    previous_views = total(previous, "views")
    recent_engaged = total(recent, "engagedViews")
    previous_engaged = total(previous, "engagedViews")
    growth = None if previous_views <= 0 else round((recent_views - previous_views) / previous_views * 100, 2)

    by_engaged = sorted(videos, key=lambda row: as_number(row.get("engagedViews")), reverse=True)
    by_retention = sorted(
        [row for row in videos if row.get("averageViewPercentage") not in (None, "")],
        key=lambda row: as_number(row.get("averageViewPercentage")),
        reverse=True,
    )
    topic_performance = aggregate_groups(
        [row for row in videos if row.get("topic")], "topic"
    )
    hook_performance = aggregate_groups(
        [row for row in videos if row.get("hook_type") and row.get("hook_type") != "unknown"], "hook_type"
    )

    recommendations = []
    if growth is not None:
        direction = "increased" if growth > 0 else "decreased" if growth < 0 else "was flat"
        recommendations.append(
            f"Shorts public views {direction} by {abs(growth):.1f}% in the latest 14-day window versus the previous 14 days."
        )
    if topic_performance:
        recommendations.append(
            "Compare the leading topic groups with the channel median, then use their factual angle and visual treatment as candidates for the next topic batch."
        )
    if any(item["sample_count"] >= 3 for item in hook_performance):
        recommendations.append(
            "There are at least three examples in one or more hook categories; compare their engaged-view and retention results before prioritizing a hook style."
        )
    elif by_engaged:
        recommendations.append(
            "Review the top three Shorts by engaged views and inspect their opening hooks before changing the next batch."
        )
    if by_retention:
        recommendations.append(
            "Use the top-retention Shorts as reference examples; compare like-for-like video ages and lengths rather than copying a single outlier."
        )
    if metadata_warning:
        recommendations.append(
            "Topic and hook attribution is incomplete because the durable upload ledger could not be joined: " + metadata_warning
        )
    recommendations.append(
        "Keep the current production count until a comparable sample supports a change; views alone do not prove that a topic or hook caused the result."
    )

    result = {
        "status": "completed",
        "period": {"start": source.get("start_date"), "end": source.get("end_date")},
        "comparison": {
            "recent_14_day_views": int(recent_views),
            "previous_14_day_views": int(previous_views),
            "views_change_percent": growth,
            "recent_14_day_engaged_views": int(recent_engaged),
            "previous_14_day_engaged_views": int(previous_engaged),
        },
        "metadata_join_coverage": {
            "videos_with_topic_and_hook": sum(1 for row in videos if row.get("topic") and row.get("hook_type")),
            "videos_in_analytics": len(videos),
            "warning": metadata_warning,
        },
        "top_by_engaged_views": by_engaged[:10],
        "top_by_average_view_percentage": by_retention[:10],
        "topic_performance": topic_performance,
        "hook_performance": hook_performance,
        "recommendations": recommendations,
        "limitations": [
            "This report describes associations; it does not prove that a hook, topic, title, or publication time caused a result.",
            "The engagedViews/views ratio is a directional proxy, not the exact YouTube Studio Stayed to watch metric.",
            "Video-level data should be compared at similar publication ages and durations.",
            "Hook categories are simple text heuristics and are not a semantic evaluation of the opening."
        ],
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Weekly Shorts Optimization",
        "",
        f"Period: {result['period']['start']} to {result['period']['end']}",
        "",
        "## Performance comparison",
        "",
        f"- Recent 14-day views: {int(recent_views):,}",
        f"- Previous 14-day views: {int(previous_views):,}",
        f"- Change: {growth if growth is not None else 'not available'}%",
        f"- Recent engaged views: {int(recent_engaged):,}",
        "",
        "## Leading topics",
        "",
    ]
    for row in topic_performance[:10]:
        lines.append(f"- {row['topic']}: {row['engagedViews']:,} engaged views across {row['sample_count']} Shorts")
    lines.extend(["", "## Hook category performance", ""])
    for row in hook_performance:
        lines.append(f"- {row['hook_type']}: {row['engagedViews']:,} engaged views across {row['sample_count']} Shorts")
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {item}" for item in recommendations)
    lines.extend(["", "## Top Shorts by engaged views", ""])
    for row in by_engaged[:10]:
        label = row.get("title") or row.get("video", "Unknown video")
        topic = row.get("topic") or "topic unavailable"
        lines.append(f"- [{label}]({row['video_url']}) — {topic}; {int(as_number(row.get('engagedViews'))):,} engaged views")
    Path(args.markdown).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("WEEKLY_OPTIMIZATION_SAVED")


if __name__ == "__main__":
    main()
