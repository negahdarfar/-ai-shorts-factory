#!/usr/bin/env python3
"""Upload exactly four validated Shorts as PRIVATE YouTube QA videos.

This is deliberately a private-only connection test. It never publishes publicly.
"""
import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
EXPECTED_COUNT = 4


def load_validated_videos(home: Path) -> list[Path]:
    report_path = Path("mpt_quality_report.json")
    if not report_path.is_file():
        raise SystemExit("Missing mpt_quality_report.json; run video validation before upload.")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Could not read the video quality report: {exc}")
    if not isinstance(report, list) or len(report) != EXPECTED_COUNT:
        raise SystemExit(f"Expected exactly {EXPECTED_COUNT} validated report entries.")

    available = {
        path.name: path
        for path in (home / "storage" / "tasks").glob("**/final-*.mp4")
        if path.is_file()
    }
    videos = []
    for item in report:
        name = item.get("file") if isinstance(item, dict) else None
        path = available.get(name)
        if path is None:
            raise SystemExit(f"Validated video is missing from storage: {name!r}")
        if path.stat().st_size < 500_000:
            raise SystemExit(f"Video is unexpectedly small; refusing upload: {path.name}")
        videos.append(path)

    if len({p.resolve() for p in videos}) != EXPECTED_COUNT:
        raise SystemExit("The validation report does not identify four distinct video files.")
    if len(available) != EXPECTED_COUNT:
        raise SystemExit(f"Expected exactly four final MP4 files in storage, found {len(available)}.")
    return videos


def main() -> None:
    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        raise SystemExit("Missing GitHub Actions secrets: " + ", ".join(missing))

    home = Path(os.environ.get("MPT_HOME", "mpt-runtime"))
    videos = load_validated_videos(home)

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"].strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"].strip(),
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"].strip(),
        scopes=SCOPES,
    )
    credentials.refresh(Request())
    if not credentials.valid or not credentials.token:
        raise SystemExit("Google did not return a valid access token.")

    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    results = []
    for index, video_path in enumerate(videos, start=1):
        body = {
            "snippet": {
                "title": f"PRIVATE QA TEST {index}/4 — Shorts Factory",
                "description": (
                    "Private technical connection test from the YouTube Shorts Factory. "
                    "This video is private and is not intended for public viewing."
                ),
                "categoryId": "22",
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(
            str(video_path), mimetype="video/mp4",
            chunksize=8 * 1024 * 1024, resumable=True
        )
        request = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(
                    f"Private QA upload {index}/{EXPECTED_COUNT}: "
                    f"{int(status.progress() * 100)}%"
                )

        video_id = response.get("id")
        if not video_id:
            raise SystemExit(
                f"YouTube returned no video ID for upload {index}; "
                "the upload cannot be confirmed."
            )
        result = {
            "index": index,
            "file": video_path.name,
            "video_id": video_id,
            "privacy": "private",
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }
        results.append(result)
        Path("youtube_private_upload_results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"PRIVATE_UPLOAD_SUCCEEDED {index}/{EXPECTED_COUNT}: {video_id}")

    if len(results) != EXPECTED_COUNT:
        raise SystemExit(f"Only {len(results)} of {EXPECTED_COUNT} private uploads completed.")
    print("ALL_FOUR_PRIVATE_UPLOADS_SUCCEEDED")
    print("All four videos were uploaded as PRIVATE. No public video was published.")


if __name__ == "__main__":
    try:
        main()
    except HttpError as error:
        print(f"YouTube API returned HTTP {error.resp.status}.", file=sys.stderr)
        print(error.content.decode("utf-8", errors="replace")[:3000], file=sys.stderr)
        raise SystemExit(1)
