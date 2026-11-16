#!/usr/bin/env python3
"""Upload exactly one private test Short using a stored OAuth refresh token."""
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise SystemExit("Missing GitHub Actions secrets: " + ", ".join(missing))

    home = Path(os.environ.get("MPT_HOME", "mpt-runtime"))
    videos = sorted((home / "storage" / "tasks").glob("**/final-*.mp4"))
    if not videos:
        raise SystemExit("No validated final-*.mp4 video was found.")
    video_path = videos[0]

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"].strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"].strip(),
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"].strip(),
        scopes=SCOPES,
    )
    credentials.refresh(Request())

    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    body = {
        "snippet": {
            "title": "Private upload test — Shorts Factory",
            "description": (
                "Private technical test upload from the YouTube Shorts Factory. "
                "This video is not intended for public viewing."
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
        str(video_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True
    )
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Private test upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    if not video_id:
        raise SystemExit("YouTube returned no video ID; upload could not be confirmed.")
    print("PRIVATE_TEST_UPLOAD_SUCCEEDED")
    print("Video ID: " + video_id)
    print("Privacy: private")
    print("Uploaded file: " + video_path.name)


if __name__ == "__main__":
    try:
        main()
    except HttpError as error:
        print(f"YouTube API returned HTTP {error.resp.status}.", file=sys.stderr)
        print(error.content.decode("utf-8", errors="replace")[:3000], file=sys.stderr)
        raise SystemExit(1)
