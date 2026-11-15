#!/usr/bin/env python3
"""Fail the quality workflow if outputs are missing, malformed, repeated or not vertical."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

home = Path(os.environ["MPT_HOME"])
expected = int(os.environ.get("EXPECTED_COUNT", "4"))
files = sorted((home / "storage" / "tasks").glob("**/final-*.mp4"))
if len(files) != expected:
    raise SystemExit(f"Expected {expected} finished MP4 files, found {len(files)}.")

hashes = set()
report = []
for path in files:
    if path.stat().st_size < 500_000:
        raise SystemExit(f"Output is suspiciously small: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
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
    width, height = int(video["width"]), int(video["height"])
    if height <= width or abs((width / height) - (9 / 16)) > 0.025:
        raise SystemExit(f"Not a proper 9:16 vertical video ({width}x{height}): {path}")
    duration = float(info["format"]["duration"])
    if not 10 <= duration <= 180:
        raise SystemExit(f"Unexpected Shorts duration ({duration:.1f}s): {path}")
    report.append({
        "file": path.name, "duration_seconds": round(duration, 1),
        "resolution": f"{width}x{height}", "size_mb": round(path.stat().st_size / 1_000_000, 2)
    })

Path("mpt_quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
for row in report:
    print(f"PASS {row['file']} | {row['resolution']} | {row['duration_seconds']}s | {row['size_mb']} MB")
print(f"Validated {len(report)} distinct vertical videos. Topic relevance and visual quality still require human review.")
