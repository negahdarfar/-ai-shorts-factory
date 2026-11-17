#!/usr/bin/env python3
"""Translate generated English SRT captions to Persian and burn them in above the English captions."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
RETRYABLE_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}
SRT_BLOCK = re.compile(r"(?ms)^\s*(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3})\s*\n(.*?)(?=\n\s*\n|\Z)")


def parse_srt(path):
    raw = path.read_text(encoding="utf-8-sig")
    rows = []
    for match in SRT_BLOCK.finditer(raw):
        cue = " ".join(line.strip() for line in match.group(3).splitlines() if line.strip())
        if cue:
            rows.append({"index": int(match.group(1)), "timing": match.group(2), "text": cue})
    if not rows:
        raise RuntimeError(f"No readable subtitle cues in {path}")
    return rows


def translate(rows, model, key):
    prompt = (
        "Translate each English subtitle cue into natural, concise Persian (Farsi). Preserve meaning, names, numbers, and tone. "
        'Return ONLY JSON: {"translations":[{"index":1,"text":"..."}]}. '
        "Return exactly one translation for every input index, in order. Do not merge cues or add explanations. "
        "Keep each Persian cue short enough to read on a phone. Input cues: "
        + json.dumps(rows, ensure_ascii=False)
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}
    request_data = json.dumps(payload).encode("utf-8")
    request_url = f"{API_ROOT}/{model}:generateContent?key={key}"
    max_attempts = max(1, int(os.getenv("GEMINI_SUBTITLE_MAX_ATTEMPTS", "6")))
    base_delay = max(1.0, float(os.getenv("GEMINI_SUBTITLE_RETRY_BASE_SECONDS", "15")))

    response_data = None
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            request_url,
            data=request_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                response_data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            if exc.code not in RETRYABLE_HTTP_STATUSES or attempt >= max_attempts:
                raise RuntimeError(f"Gemini translation failed after {attempt} attempt(s): HTTP {exc.code}: {detail}") from exc
            retry_after = 0.0
            try:
                retry_after = float(exc.headers.get("Retry-After", "0"))
            except (TypeError, ValueError):
                pass
            delay = min(180.0, max(base_delay * (2 ** (attempt - 1)), retry_after))
            print(
                f"GEMINI_TEMPORARY_HTTP_{exc.code}; retry {attempt + 1}/{max_attempts} in {delay:.0f}s",
                flush=True,
            )
            time.sleep(delay)
        except urllib.error.URLError as exc:
            if attempt >= max_attempts:
                raise RuntimeError(f"Gemini connection failed after {attempt} attempt(s): {exc}") from exc
            delay = min(180.0, base_delay * (2 ** (attempt - 1)))
            print(
                f"GEMINI_TEMPORARY_CONNECTION_ERROR; retry {attempt + 1}/{max_attempts} in {delay:.0f}s",
                flush=True,
            )
            time.sleep(delay)

    if response_data is None:
        raise RuntimeError("Gemini translation ended without a response.")

    parts = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    raw = "\n".join(part.get("text", "") for part in parts)
    raw = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw.strip(), flags=re.I)
    parsed = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    mapping = {int(row["index"]): str(row["text"]).strip() for row in parsed.get("translations", [])}
    expected = {row["index"] for row in rows}
    if set(mapping) != expected or any(not mapping[index] for index in expected):
        raise RuntimeError("Persian translation returned missing or empty subtitle cues.")
    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.getenv("SEO_GEMINI_MODEL", "gemini-3.8-flash"))
    parser.add_argument("--home", default=os.getenv("MPT_HOME", "mpt-runtime"))
    args = parser.parse_args()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise SystemExit("GEMINI_API_KEY missing; Persian subtitle generation is mandatory.")
    root = Path(args.home) / "storage" / "tasks"
    videos = sorted(root.glob("**/final-*.mp4"))
    if len(videos) != 4:
        raise SystemExit(f"Expected four final videos before Persian subtitle processing, found {len(videos)}.")
    for index, video in enumerate(videos, 1):
        english = video.parent / "subtitle.srt"
        if not english.is_file():
            raise SystemExit(f"English subtitle source missing for video {index}: {english}")
        cues = parse_srt(english)
        translations = translate(cues, args.model, key)
        persian = video.parent / "subtitle.fa.srt"
        blocks = [
            f"{cue['index']}\n{cue['timing']}\n{translations[cue['index']]}\n"
            for cue in cues
        ]
        persian.write_text("\n".join(blocks), encoding="utf-8")
        temporary = video.with_name(video.stem + ".fa-tmp.mp4")
        escaped = str(persian.resolve()).replace("\\", "/").replace(":", "\\:")
        vf = (
            f"subtitles='{escaped}':force_style='FontName=Noto Naskh Arabic,"
            "FontSize=18,Alignment=8,MarginV=42,Outline=2,Shadow=0,"
            "BorderStyle=3,BackColour=&H90000000'"
        )
        command = [
            "ffmpeg", "-y", "-i", str(video), "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
            str(temporary),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            temporary.unlink(missing_ok=True)
            raise SystemExit(
                f"Persian subtitle burn-in failed for video {index}: "
                f"{(result.stderr or result.stdout)[-2500:]}"
            )
        if not temporary.is_file() or temporary.stat().st_size < 500_000:
            raise SystemExit(f"Persian-subtitled output invalid for video {index}.")
        temporary.replace(video)
        print(f"PERSIAN_SUBTITLES_BURNED_IN {index}/4 | cues={len(cues)} | {video.name}")
    print("PERSIAN_SUBTITLES_COMPLETED_FOR_ALL_FOUR_VIDEOS")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"PERSIAN_SUBTITLE_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
