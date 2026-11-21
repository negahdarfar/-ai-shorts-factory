#!/usr/bin/env python3
"""Build a self-contained HTML dashboard from Shorts analytics and optimization JSON."""
import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    candidate = Path(path)
    return json.loads(candidate.read_text(encoding="utf-8")) if candidate.is_file() else {}


def table_rows(report, limit=20):
    headers = [item.get("name", "") for item in report.get("columnHeaders", [])]
    rows = report.get("rows", [])
    rendered = []
    for row in rows[:limit]:
        values = dict(zip(headers, row))
        if "video" in values:
            video_id = html.escape(str(values["video"]))
            values["video"] = f'<a href="https://www.youtube.com/watch?v={video_id}" target="_blank" rel="noopener">{video_id}</a>'
        rendered.append("<tr>" + "".join(f"<td>{values.get(k, '') if k == 'video' else html.escape(str(values.get(k, '')))}</td>" for k in headers) + "</tr>")
    head = "".join(f"<th>{html.escape(str(item))}</th>" for item in headers)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rendered)}</tbody></table>" if headers else "<p>No rows returned.</p>"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analytics", default="youtube_analytics.json")
    parser.add_argument("--optimization", default="weekly_optimization.json")
    parser.add_argument("--output", default="factory_dashboard.html")
    args = parser.parse_args()
    analytics = load_json(args.analytics)
    optimization = load_json(args.optimization)
    status = analytics.get("status", "BLOCKED")
    period = f"{analytics.get('start_date', '—')} → {analytics.get('end_date', '—')}"
    reports = analytics.get("reports", {})
    daily = reports.get("shorts_daily", {})
    videos = reports.get("shorts_videos", {})
    recommendations = optimization.get("recommendations", [])
    rec_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in recommendations) or "<li>Analytics authorization or data is not available yet.</li>"
    blocked = analytics.get("reason") or "Add YOUTUBE_ANALYTICS_REFRESH_TOKEN with yt-analytics.readonly consent to enable channel analytics."
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KOROUSH VIRAL SHORTS FACTORY — Dashboard</title>
<style>
:root{{color-scheme:dark;--bg:#0b1020;--panel:#151d32;--line:#293550;--text:#edf2ff;--muted:#aab6d0;--accent:#8fb4ff}}
*{{box-sizing:border-box}}body{{margin:0;padding:28px;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--text)}}
main{{max-width:1200px;margin:auto}}h1{{font-size:26px;margin:0}}h2{{font-size:18px;margin:0 0 14px}}p,.muted{{color:var(--muted)}}
header{{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:24px;flex-wrap:wrap}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:18px 0}}
.card,section{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}}
.value{{font-size:25px;font-weight:700}}.status{{color:var(--accent);font-weight:700}}
table{{width:100%;border-collapse:collapse;font-size:13px;display:block;overflow-x:auto}}td,th{{padding:9px 11px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}
th{{color:var(--muted)}}a{{color:var(--accent)}}li{{margin:8px 0}}footer{{color:var(--muted);font-size:12px;margin-top:24px}}
</style></head><body><main>
<header><div><h1>KOROUSH VIRAL SHORTS FACTORY</h1><p>Channel analytics and weekly optimization</p></div><div class="status">{html.escape(status.upper())}</div></header>
<div class="grid">
<div class="card"><div class="muted">Reporting period</div><div class="value" style="font-size:16px">{html.escape(period)}</div></div>
<div class="card"><div class="muted">Analytics status</div><div class="value">{html.escape(status.upper())}</div></div>
<div class="card"><div class="muted">Shorts daily rows</div><div class="value">{len(daily.get('rows', []))}</div></div>
<div class="card"><div class="muted">Shorts video rows</div><div class="value">{len(videos.get('rows', []))}</div></div>
</div>
<section><h2>Weekly recommendations</h2><ul>{rec_html}</ul></section>
<section><h2>Shorts performance by day</h2>{table_rows(daily, 45)}</section>
<section><h2>Shorts performance by video</h2>{table_rows(videos, 50)}</section>
{f'<section><h2>Setup required</h2><p>{html.escape(str(blocked))}</p></section>' if status != 'completed' else ''}
<footer>Generated {datetime.now(timezone.utc).isoformat()} · Public views and engaged views are different metrics. See the metric notes in youtube_analytics.json.</footer>
</main></body></html>"""
    Path(args.output).write_text(body, encoding="utf-8")
    print(f"FACTORY_DASHBOARD_SAVED {args.output}")


if __name__ == "__main__":
    main()
