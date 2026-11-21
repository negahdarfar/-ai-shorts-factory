#!/usr/bin/env python3
"""Technical Shorts quality gate: duration, 9:16, audio, captions, black frames and silence."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

home = Path(os.environ["MPT_HOME"])
expected = int(os.environ.get("EXPECTED_COUNT", "4"))
if not 4 <= expected <= 10:
    raise SystemExit("EXPECTED_COUNT must be between 4 and 10.")

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
    streams = info.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video or not audio_stream:
        raise SystemExit(f"Missing video or audio stream: {path}")

    width, height = int(video["width"]), int(video["height"])
    if height <= width or abs((width / height) - (9 / 16)) > 0.025:
        raise SystemExit(f"Not a proper 9:16 vertical video ({width}x{height}): {path}")
    if width < 720 or height < 1280:
        raise SystemExit(f"Resolution below 720x1280 minimum: {width}x{height}: {path}")

    duration = float(info["format"]["duration"])
    if not 60 <= duration <= 120:
        raise SystemExit(f"Shorts duration must be 60-120 seconds ({duration:.1f}s): {path}")

    subtitles = path.parent / "subtitle.fa.srt"
    if not subtitles.is_file() or subtitles.stat().st_size < 20:
        raise SystemExit(f"Missing or empty Persian subtitle file: {subtitles}")
    subtitle_text = subtitles.read_text(encoding="utf-8-sig").strip()
    if "-->" not in subtitle_text or not any(0x0600 <= ord(char) <= 0x06ff for char in subtitle_text):
        raise SystemExit(f"Persian subtitle file has no valid timing or Persian-script text: {subtitles}")

    scan = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-v", "info", "-i", str(path),
            "-vf", "blackdetect=d=1.5:pix_th=0.10",
            "-af", "silencedetect=n=-50dB:d=2.0",
            "-f", "null", "-"
        ],
        capture_output=True, text=True, check=False
    )
    if scan.returncode != 0:
        raise SystemExit(f"FFmpeg black-frame/silence scan failed for {path}: {scan.stderr[-1200:]}")
    diagnostics = (scan.stderr or "") + (scan.stdout or "")
    black_durations = [float(value) for value in re.findall(r"black_duration:([0-9.]+)", diagnostics)]
    silence_starts = [float(value) for value in re.findall(r"silence_start: ([0-9.]+)", diagnostics)]
    silence_ends = [float(value) for value in re.findall(r"silence_end: ([0-9.]+)", diagnostics)]
    black_total = sum(black_durations)
    silence_total = sum(max(0.0, end - start) for start, end in zip(silence_starts, silence_ends))
    if len(silence_starts) > len(silence_ends):
        silence_total += max(0.0, duration - silence_starts[-1])
    if black_total > max(3.0, duration * 0.03):
        raise SystemExit(f"Excessive black-frame duration ({black_total:.1f}s): {path}")
    if silence_total > max(6.0, duration * 0.08):
        raise SystemExit(f"Excessive detected silence ({silence_total:.1f}s): {path}")

    score = 100
    if width < 1080 or height < 1920:
        score -= 10
    if black_total > 0:
        score -= 5
    if silence_total > 0:
        score -= 5
    if score < 85:
        raise SystemExit(f"QUALITY_GATE_FAILED score={score}/100: {path}")

    report.append({
        "file": path.name,
        "relative_path": path.relative_to(tasks_root).as_posix(),
        "sha256": digest,
        "duration_seconds": round(duration, 1),
        "resolution": f"{width}x{height}",
        "video_codec": video.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "audio_sample_rate": audio_stream.get("sample_rate"),
        "size_mb": round(path.stat().st_size / 1_000_000, 2),
        "persian_subtitles": str(subtitles.relative_to(tasks_root)),
        "detected_black_seconds": round(black_total, 2),
        "detected_silence_seconds": round(silence_total, 2),
        "quality_score": score,
    })

Path("mpt_quality_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
for row in report:
    print(
        "PASS {} | {} | {}s | {} MB | QUALITY_SCORE={}/100".format(
            row["relative_path"], row["resolution"], row["duration_seconds"],
            row["size_mb"], row["quality_score"]
        )
    )
print(
    f"QUALITY_GATE_PASSED: {len(report)} distinct vertical Shorts; "
    f"average score={sum(row['quality_score'] for row in report) / len(report):.1f}/100. "
    "Factual accuracy and creative value still require editorial review."
)
