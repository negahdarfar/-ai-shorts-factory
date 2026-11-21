#!/usr/bin/env python3
"""Create conservative, data-backed weekly Shorts recommendations from Analytics exports."""
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
    for row in report.get("rows", []):
        if len(row) != len(headers):
            continue
        output.append(dict(zip(headers, row)))
    return output


def total(rows, key):
    return sum(as_number(row.get(key)) for row in rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="youtube_analytics.json")
    parser.add_argument("--output", default="weekly_optimization.json")
    parser.add_argument("--markdown", default="weekly_optimization.md")
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

    for row in videos:
        row["engaged_views_over_views_percent"] = (
            round(100 * as_number(row.get("engagedViews")) / as_number(row.get("views")), 2)
            if as_number(row.get("views")) > 0 else None
        )
        row["video_url"] = "https://www.youtube.com/watch?v=" + str(row.get("video", ""))

    by_engaged = sorted(videos, key=lambda row: as_number(row.get("engagedViews")), reverse=True)
    by_retention = sorted(
        [row for row in videos if row.get("averageViewPercentage") not in (None, "")],
        key=lambda row: as_number(row.get("averageViewPercentage")),
        reverse=True,
    )
    recommendations = []
    if growth is not None:
        direction = "increased" if growth > 0 else "decreased" if growth < 0 else "was flat"
        recommendations.append(
            f"Shorts public views {direction} by {abs(growth):.1f}% in the latest 14-day window versus the previous 14 days."
        )
    if by_engaged:
        recommendations.append(
            "Review the top three Shorts by engaged views and identify their topic, opening hook, and visual pacing before changing the next batch."
        )
    if by_retention:
        recommendations.append(
            "Use the top-retention Shorts as reference examples; compare like-for-like video ages and lengths rather than copying a single outlier."
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
        "top_by_engaged_views": by_engaged[:10],
        "top_by_average_view_percentage": by_retention[:10],
        "recommendations": recommendations,
        "limitations": [
            "This report describes associations; it does not prove that a hook, topic, title, or publication time caused a result.",
            "The engagedViews/views ratio is a directional proxy, not the exact YouTube Studio Stayed to watch metric.",
            "Video-level data should be compared at similar publication ages and durations.",
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
        "## Recommendations",
        "",
    ]
    lines.extend(f"- {item}" for item in recommendations)
    lines.extend(["", "## Top Shorts by engaged views", ""])
    for row in by_engaged[:10]:
        lines.append(f"- [{row.get('video', 'Unknown video')}]({row['video_url']}) — {int(as_number(row.get('engagedViews'))):,} engaged views")
    Path(args.markdown).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("WEEKLY_OPTIMIZATION_SAVED")


if __name__ == "__main__":
    main()
