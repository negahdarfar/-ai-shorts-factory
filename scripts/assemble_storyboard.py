#!/usr/bin/env python3
"""Build a long-form timeline from licensed still images and short video clips.

Manifest entries may be legacy video path strings or objects:
{"path":"assets/scene.jpg","type":"image","duration":8,"motion":"zoom_in"}
{"path":"assets/clip.mp4","type":"video","start":2,"end":14}
All scenes are normalized to silent 1080p/30fps segments before concatenation.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

WIDTH, HEIGHT, FPS = 1920, 1080, 30
IMAGE_MOTIONS = {"zoom_in", "zoom_out", "pan_left", "pan_right", "static"}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def media_duration(path: str | Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def load_scenes(manifest_path: str | Path) -> list[dict]:
    try:
        raw = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read storyboard manifest: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise ValueError("Storyboard manifest must be a non-empty JSON array.")
    scenes = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            scene = {"path": item, "type": "video"}
        elif isinstance(item, dict):
            scene = dict(item)
        else:
            raise ValueError(f"Scene {index} must be a path string or object.")
        path = scene.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"Scene {index} requires a non-empty path.")
        kind = scene.get("type") or ("image" if Path(path).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"} else "video")
        if kind not in {"image", "video"}:
            raise ValueError(f"Scene {index} has unsupported type: {kind}")
        scene["type"] = kind
        if kind == "image":
            duration = float(scene.get("duration", 6))
            motion = scene.get("motion", "zoom_in")
            if not 1 <= duration <= 120:
                raise ValueError(f"Image scene {index} duration must be between 1 and 120 seconds.")
            if motion not in IMAGE_MOTIONS:
                raise ValueError(f"Image scene {index} has unsupported motion: {motion}")
            scene["duration"] = duration
            scene["motion"] = motion
        else:
            start = float(scene.get("start", 0))
            end = scene.get("end")
            if start < 0 or (end is not None and float(end) <= start):
                raise ValueError(f"Video scene {index} requires end > start >= 0.")
            scene["start"] = start
            if end is not None:
                scene["end"] = float(end)
        scenes.append(scene)
    return scenes


def _image_filter(scene: dict) -> str:
    frames = max(1, round(scene["duration"] * FPS))
    motion = scene["motion"]
    zoom = {
        "zoom_in": "min(zoom+0.0008,1.12)",
        "zoom_out": "if(eq(on,0),1.12,max(1.0,zoom-0.0008))",
        "pan_left": "1.10",
        "pan_right": "1.10",
        "static": "1.0",
    }[motion]
    x = {
        "pan_left": "iw/2-(iw/zoom/2)+((iw-iw/zoom)*(1-on/{}) )".format(frames),
        "pan_right": "iw/2-(iw/zoom/2)+((iw-iw/zoom)*(on/{}) )".format(frames),
    }.get(motion, "iw/2-(iw/zoom/2)")
    return (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1,"
        f"zoompan=z='{zoom}':x='{x}':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p"
    )


def render_scene(scene: dict, source: Path, target: Path) -> None:
    if scene["type"] == "image":
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(source), "-vf", _image_filter(scene),
            "-frames:v", str(round(scene["duration"] * FPS)),
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", "-r", str(FPS), str(target),
        ])
        return
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(scene["start"]), "-i", str(source)]
    if scene.get("end") is not None:
        command += ["-t", str(scene["end"] - scene["start"])]
    command += [
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
               f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS},format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p", "-r", str(FPS), str(target),
    ]
    run(command)


def assemble(manifest: str | Path, output: str | Path, voiceover: str | Path | None = None, subtitles: str | Path | None = None, burn_subtitles: bool = False) -> dict:
    scenes = load_scenes(manifest)
    root = Path(manifest).resolve().parent.parent
    sources = []
    for index, scene in enumerate(scenes):
        source = (root / scene["path"]).resolve()
        if root not in source.parents or not source.is_file():
            raise ValueError(f"Scene asset is missing or outside repository: {scene['path']}")
        scene["_source"] = source
        sources.append(source)
    out = Path(output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="storyboard-") as tmp:
        temp = Path(tmp)
        segments = []
        for index, scene in enumerate(scenes):
            segment = temp / f"scene_{index:05d}.mp4"
            render_scene(scene, scene["_source"], segment)
            segments.append(segment)
        concat = temp / "concat.txt"
        concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
        joined = temp / "joined.mp4"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(joined)])
        audio = Path(voiceover).resolve() if voiceover else None
        if audio and not audio.is_file():
            raise ValueError(f"Voiceover file not found: {audio}")
        if audio:
            video_seconds = media_duration(joined)
            voice_seconds = media_duration(audio)
            if voice_seconds > video_seconds + 0.5:
                raise ValueError(
                    f"Voiceover ({voice_seconds:.1f}s) exceeds storyboard duration "
                    f"({video_seconds:.1f}s); add scenes rather than truncating narration."
                )
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(joined), "-i", str(audio),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                "-ar", "48000", "-ac", "2", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,apad",
                "-shortest", "-movflags", "+faststart", str(out),
            ])
        else:
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(joined),
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                "-shortest", "-movflags", "+faststart", str(out),
            ])
        if subtitles and burn_subtitles:
            subtitle_path = Path(subtitles).resolve()
            if not subtitle_path.is_file():
                raise ValueError(f"Subtitle file not found: {subtitle_path}")
            escaped = str(subtitle_path).replace(chr(92), chr(92) * 2).replace(":", chr(92) + ":").replace("'", chr(92) + "'")
            filter_arg = f"subtitles='{escaped}':force_style='FontName=Noto Naskh Arabic,FontSize=28,Outline=2,Shadow=1,Alignment=2,MarginV=42,WrapStyle=2'"
            subtitled = temp / "subtitled.mp4"
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(out),
                "-vf", filter_arg, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(subtitled),
            ])
            subtitled.replace(out)
    return {
        "status": "assembled",
        "scene_count": len(scenes),
        "image_scenes": sum(s["type"] == "image" for s in scenes),
        "video_scenes": sum(s["type"] == "video" for s in scenes),
        "output": str(out),
        "audio": "voiceover" if audio else "silent_track",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", "--clips", dest="manifest", required=True)
    parser.add_argument("--output", default="longform-output/documentary.mp4")
    parser.add_argument("--voiceover")
    parser.add_argument("--subtitles")
    parser.add_argument("--burn-subtitles", action="store_true")
    args = parser.parse_args()
    try:
        result = assemble(args.manifest, args.output, args.voiceover, args.subtitles, args.burn_subtitles)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"STORYBOARD_ASSEMBLY_FAILED: {exc}") from exc
    print("STORYBOARD_ASSEMBLY_SUCCEEDED")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
