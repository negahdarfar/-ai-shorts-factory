#!/usr/bin/env python3
"""Fail the quality workflow if outputs are missing, malformed, repeated or not vertical."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

home = Path(os.environ["MPT_HOME"])
expected = int(os.environ.get("EXPECTED_COUNT", "4"))
tasks_root = home / "storage" / "tasks"
files = sorted(tasks_root.glob("**/final-*.mp4"))
if len(files) != expected:
    raise SystemExit(f"Expected {expected} finished MP4 files, found {len(files)}.")

hashes = set()
report = []
for path in files:
    if path.stat().st_size < 500_000:
        raise SystemExit(f"Output is suspiciously small: {path}")
    hasher = hashlib.sha256()
    with path.open("rb") as video_file:
        for chunk in iter(lambda: video_file.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if digest in hashes:
        raise SystemExit(f"Duplicate video output detected: {path}")
    hashes.add(digest)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True
    )
    info = json.loads(probe.stdout)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    if not video or not audio:
        raise SystemExit(f"Missing video or audio stream: {path}")
    persian_subtitles = path.parent / "subtitle.fa.srt"
    if not persian_subtitles.is_file() or persian_subtitles.stat().st_size < 20:
        raise SystemExit(f"Missing or empty Persian subtitle file: {persian_subtitles}")
    subtitle_text = persian_subtitles.read_text(encoding="utf-8-sig").strip()
    if "-->" not in subtitle_text or not any(0x0600 <= ord(char) <= 0x06ff for char in subtitle_text):
        raise SystemExit(f"Persian subtitle file has no valid timing or Persian-script text: {persian_subtitles}")
    width, height = int(video["width"]), int(video["height"])
    if height <= width or abs((width / height) - (9 / 16)) > 0.025:
        raise SystemExit(f"Not a proper 9:16 vertical video ({width}x{height}): {path}")
    duration = float(info["format"]["duration"])
    if not 45 <= duration <= 60:
        raise SystemExit(f"Shorts duration must be 45-60 seconds ({duration:.1f}s): {path}")
    report.append({
        "file": path.name,
        "relative_path": path.relative_to(tasks_root).as_posix(),
        "duration_seconds": round(duration, 1),
        "resolution": f"{width}x{height}",
        "size_mb": round(path.stat().st_size / 1_000_000, 2),
        "persian_subtitles": str(persian_subtitles.relative_to(tasks_root)),
    })

Path("mpt_quality_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
for row in report:
    print(
        "PASS {} | {} | {}s | {} MB".format(
            row["relative_path"], row["resolution"], row["duration_seconds"], row["size_mb"]
        )
    )
print(
    f"Validated {len(report)} distinct vertical videos. "
    "Topic relevance and visual quality still require human review."
)
