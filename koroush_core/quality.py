"""Shared media quality gates for Koroush AI factories."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

class QualityError(RuntimeError):
    pass

def inspect_media(path: str | Path) -> dict:
    file = Path(path)
    if not file.is_file() or file.stat().st_size <= 0:
        raise QualityError(f"Missing or empty media file: {file}")
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-of", "json", str(file)],
            check=True, capture_output=True, text=True, timeout=30,
        )
        data = json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise QualityError(f"ffprobe could not inspect {file}: {exc}") from exc
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None:
        raise QualityError("No video stream found.")
    duration = float((data.get("format") or {}).get("duration") or 0)
    if duration <= 0:
        raise QualityError("Invalid or missing media duration.")
    return {
        "path": str(file), "size_bytes": file.stat().st_size,
        "duration_seconds": duration,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "has_audio": audio is not None,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name") if audio else None,
    }

def validate_media(path: str | Path, *, min_duration: float = 1,
                   max_duration: float | None = None,
                   aspect: str | None = None, require_audio: bool = True) -> dict:
    report = inspect_media(path)
    if report["duration_seconds"] < min_duration:
        raise QualityError(f"Duration below minimum ({min_duration}s).")
    if max_duration is not None and report["duration_seconds"] > max_duration:
        raise QualityError(f"Duration exceeds maximum ({max_duration}s).")
    if require_audio and not report["has_audio"]:
        raise QualityError("Audio stream is required but missing.")
    if aspect == "9:16" and report["height"] <= report["width"]:
        raise QualityError("Expected vertical 9:16 video.")
    if aspect == "16:9" and report["width"] <= report["height"]:
        raise QualityError("Expected horizontal 16:9 video.")
    return report
