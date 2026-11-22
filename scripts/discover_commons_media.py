#!/usr/bin/env python3
"""Acquire openly licensed Wikimedia Commons stills and short clips for a storyboard plan.

Only Public Domain, CC0, and CC BY assets are accepted automatically. CC BY-SA is
excluded because downstream ShareAlike compliance needs an explicit decision.
This script records provenance; it cannot prove copyright status or suitability.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "KoroushLongformStudio/1.0 (open media discovery; contact via repository)"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".webm", ".ogv", ".mp4"}
MAX_DOWNLOAD_BYTES = 80 * 1024 * 1024
MOTIONS = ("zoom_in", "pan_right", "zoom_out", "pan_left")


class CommonsError(RuntimeError):
    pass


def clean_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", str(value or ""), flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def license_family(short_name: str) -> str | None:
    value = re.sub(r"\s+", " ", str(short_name or "").strip().lower().replace("-", " "))
    if "noncommercial" in value or "no derivatives" in value or "nc" in value.split() or "nd" in value.split() or "sa" in value.split():
        return None
    if value in {"public domain", "pd", "cc0", "cc0 1.0"} or value.startswith("public domain"):
        return "public-domain"
    if re.match(r"^cc by(?:\s|$)", value):
        return "cc-by"
    # Do not auto-accept ShareAlike; it needs downstream license compatibility review.
    return None


def media_extension(url: str) -> str:
    return Path(urllib.parse.urlparse(url).path).suffix.lower()


def page_metadata(page: dict) -> dict | None:
    info_rows = page.get("imageinfo") or []
    if not info_rows or not isinstance(info_rows[0], dict):
        return None
    info = info_rows[0]
    ext = media_extension(info.get("url", ""))
    if ext not in IMAGE_EXTS | VIDEO_EXTS:
        return None
    metadata = info.get("extmetadata") or {}
    def field(name: str) -> str:
        item = metadata.get(name, {})
        return clean_html(item.get("value", "")) if isinstance(item, dict) else ""
    short = field("LicenseShortName")
    family = license_family(short)
    source_url = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(str(page.get("title", "")).replace(" ", "_"), safe=":/")
    license_url = field("LicenseUrl")
    artist = field("Artist") or field("Credit") or "Creator not stated in Commons metadata"
    title = str(page.get("title", "")).removeprefix("File:").replace("_", " ")
    if not family or not license_url.startswith("https://"):
        return None
    return {
        "title": title,
        "media_url": info.get("url", ""),
        "source_url": source_url,
        "license": short,
        "license_family": family,
        "license_url": license_url,
        "attribution": f"{artist} — {title} (Wikimedia Commons)",
        "extension": ext,
        "width": info.get("width"),
        "height": info.get("height"),
    }


def api_search(query: str, limit: int = 8, timeout: int = 25) -> list[dict]:
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": "6", "gsrlimit": str(limit), "gsrsearch": query,
        "prop": "imageinfo", "iiprop": "url|extmetadata",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise CommonsError(f"Wikimedia Commons search failed: {exc}") from exc
    pages = payload.get("query", {}).get("pages", {})
    return list(pages.values()) if isinstance(pages, dict) else []


def download_asset(url: str, target: Path, timeout: int = 60) -> int:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "upload.wikimedia.org":
        raise CommonsError("Refusing media URL outside HTTPS upload.wikimedia.org.")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, target.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise CommonsError("Media file exceeds the 80 MB download limit.")
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if total == 0:
        target.unlink(missing_ok=True)
        raise CommonsError("Downloaded media file is empty.")
    return total


def video_seconds(path: Path) -> float | None:
    if not shutil.which("ffprobe"):
        return None
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True, timeout=30,
        )
        value = float(result.stdout.strip())
        return value if value > 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def build_storyboard(plan_path: str | Path, output_manifest: str | Path,
                     output_ledger: str | Path, asset_dir: str | Path,
                     per_scene: int = 8, max_video_seconds: int = 30) -> dict:
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    chapters = plan.get("chapters") if isinstance(plan, dict) else None
    if not isinstance(chapters, list) or not chapters:
        raise CommonsError("Plan must contain a non-empty chapters array.")
    scenes = []
    for chapter in chapters:
        if not isinstance(chapter, dict) or not isinstance(chapter.get("scenes"), list):
            continue
        for scene in chapter["scenes"]:
            if isinstance(scene, dict) and str(scene.get("visual_query", "")).strip():
                scenes.append(scene)
    if not scenes:
        raise CommonsError("Plan contains no searchable visual scene briefs.")

    root = Path.cwd().resolve()
    asset_root = Path(asset_dir).resolve()
    if root not in asset_root.parents:
        raise CommonsError("Asset directory must be inside the repository.")
    manifest_rows, rights_rows, failures = [], [], []
    used_urls = set()
    for index, scene in enumerate(scenes, 1):
        query = re.sub(r"\s+", " ", str(scene["visual_query"])).strip()
        desired = scene.get("media_type", "image")
        try:
            pages = api_search(query, per_scene)
            candidates = []
            for page in pages:
                item = page_metadata(page)
                if not item or item["media_url"] in used_urls:
                    continue
                is_video = item["extension"] in VIDEO_EXTS
                if desired == "video" and not is_video:
                    continue
                if desired == "image" and is_video:
                    continue
                candidates.append(item)
            # If no video is available, a licensed still is a valid visual fallback.
            if not candidates and desired == "video":
                for page in pages:
                    item = page_metadata(page)
                    if item and item["extension"] in IMAGE_EXTS and item["media_url"] not in used_urls:
                        candidates.append(item)
            if not candidates:
                failures.append({"scene": index, "query": query, "reason": "No eligible, supported, unused media with accepted license."})
                continue
            chosen = candidates[0]
            ext = chosen["extension"]
            filename = f"commons_{index:03d}{ext}"
            target = asset_root / filename
            byte_count = download_asset(chosen["media_url"], target)
            relative = target.relative_to(root).as_posix()
            if ext in VIDEO_EXTS:
                duration = video_seconds(target)
                if not duration:
                    target.unlink(missing_ok=True)
                    failures.append({"scene": index, "query": query, "reason": "Could not safely determine video duration."})
                    continue
                clip_length = min(float(max_video_seconds), duration)
                if clip_length < 2:
                    target.unlink(missing_ok=True)
                    failures.append({"scene": index, "query": query, "reason": "Video is shorter than two seconds."})
                    continue
                manifest_rows.append({"path": relative, "type": "video", "start": 0, "end": round(clip_length, 2)})
            else:
                manifest_rows.append({
                    "path": relative, "type": "image",
                    "duration": float(scene.get("duration_seconds", 8)),
                    "motion": MOTIONS[(index - 1) % len(MOTIONS)],
                })
            rights_rows.append({
                "asset": relative,
                "source_url": chosen["source_url"],
                "license": chosen["license"],
                "license_url": chosen["license_url"],
                "attribution": chosen["attribution"],
                "discovery_provider": "Wikimedia Commons",
                "download_bytes": byte_count,
            })
            used_urls.add(chosen["media_url"])
            time.sleep(0.15)
        except (CommonsError, OSError, ValueError, KeyError) as exc:
            failures.append({"scene": index, "query": query, "reason": str(exc)[:500]})

    if not manifest_rows:
        raise CommonsError("No eligible media could be downloaded; see discovery report.")
    for path in (output_manifest, output_ledger):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_manifest).write_text(json.dumps(manifest_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(output_ledger).write_text(json.dumps(rights_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "partial" if failures else "ready",
        "requested_scenes": len(scenes),
        "downloaded_assets": len(manifest_rows),
        "failed_scenes": failures,
        "manifest": str(output_manifest),
        "rights_ledger": str(output_ledger),
        "warning": "License metadata is collected from Commons and must still be checked against the original file page and intended use. No NC, ND, unknown, or CC BY-SA files are auto-selected.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--manifest", default="data/longform/generated-storyboard.json")
    parser.add_argument("--ledger", default="data/longform/generated-rights.json")
    parser.add_argument("--assets", default="assets/longform/generated")
    parser.add_argument("--per-scene", type=int, default=8)
    parser.add_argument("--max-video-seconds", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.per_scene <= 20 or not 2 <= args.max_video_seconds <= 60:
        raise SystemExit("per-scene must be 1–20 and max-video-seconds 2–60.")
    try:
        result = build_storyboard(args.plan, args.manifest, args.ledger, args.assets, args.per_scene, args.max_video_seconds)
    except (CommonsError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"COMMONS_STORYBOARD_FAILED: {exc}") from exc
    report = Path("longform-output/commons-discovery-report.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"COMMONS_STORYBOARD_{result['status'].upper()} | assets={result['downloaded_assets']} | failures={len(result['failed_scenes'])}")
    if result["failed_scenes"]:
        print(json.dumps(result["failed_scenes"], ensure_ascii=False))


if __name__ == "__main__":
    main()
