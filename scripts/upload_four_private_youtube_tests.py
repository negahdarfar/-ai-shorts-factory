#!/usr/bin/env python3
"""Upload 4-10 validated Shorts to YouTube.

Privacy is PRIVATE by default. PUBLIC publishing is possible only when the
workflow explicitly sets YOUTUBE_PRIVACY_STATUS=public.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from topic_history import ensure_new_topics, record_published_topic

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
def configured_expected_count():
    try:
        count = int(os.environ.get("EXPECTED_COUNT", "4"))
    except ValueError as exc:
        raise SystemExit("EXPECTED_COUNT must be an integer from 4 to 10.") from exc
    if not 4 <= count <= 10:
        raise SystemExit("EXPECTED_COUNT must be between 4 and 10.")
    return count


EXPECTED_COUNT = configured_expected_count()


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

    tasks_root = home / "storage" / "tasks"
    available = {
        path.relative_to(tasks_root).as_posix(): path
        for path in tasks_root.glob("**/final-*.mp4")
        if path.is_file()
    }
    videos = []
    for item in report:
        relative_path = item.get("relative_path") if isinstance(item, dict) else None
        path = available.get(relative_path)
        if path is None:
            raise SystemExit(f"Validated video path is missing from storage: {relative_path!r}.")
        if path.stat().st_size < 500_000:
            raise SystemExit(f"Video is unexpectedly small; refusing upload: {relative_path}")
        videos.append(path)

    if len({p.resolve() for p in videos}) != EXPECTED_COUNT:
        raise SystemExit("The validation report does not identify four distinct video files.")
    if len(available) != EXPECTED_COUNT:
        raise SystemExit(f"Expected exactly {EXPECTED_COUNT} final MP4 files in storage, found {len(available)}.")
    return videos


def load_seo_manifest() -> list[dict]:
    path = Path("seo_metadata.json")
    if not path.is_file():
        raise SystemExit("Missing seo_metadata.json; refusing upload without SEO metadata.")
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != EXPECTED_COUNT:
        raise SystemExit(f"SEO manifest must contain exactly {EXPECTED_COUNT} records.")
    for index, record in enumerate(records, 1):
        meta = record.get("metadata", {}) if isinstance(record, dict) else {}
        script = str(record.get("video_script", "")).strip()
        terms = record.get("video_terms")
        if (not record.get("topic") or not meta.get("title") or not meta.get("description")
                or not 155 <= len(script.split()) <= 270 or not isinstance(terms, list) or len(terms) < 5):
            raise SystemExit(f"SEO/content manifest record {index} is incomplete; refusing upload.")
    return records


def main() -> None:
    requested_privacy = os.environ.get("YOUTUBE_PRIVACY_STATUS", "private").strip().lower()
    scheduled = os.environ.get("YOUTUBE_SCHEDULED_PUBLISH", "NO").strip().upper() == "YES"
    if requested_privacy not in {"private", "public"}:
        raise SystemExit("YOUTUBE_PRIVACY_STATUS must be either private or public.")
    if requested_privacy == "public" and os.environ.get("CONFIRM_PUBLIC_PUBLISHING") != "YES":
        raise SystemExit("Public upload blocked: explicit workflow confirmation is missing.")

    privacy = "private" if scheduled else requested_privacy
    first_publish_at = None
    if scheduled:
        candidate = datetime.now(timezone.utc) + timedelta(minutes=60)
        first_publish_at = candidate.replace(minute=0, second=0, microsecond=0)
        if first_publish_at < candidate:
            first_publish_at += timedelta(hours=1)
        print(f"SCHEDULING_PUBLIC_SHORTS: count={EXPECTED_COUNT} | first slot {first_publish_at.isoformat()}")

    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        raise SystemExit("Missing GitHub Actions secrets: " + ", ".join(missing))

    home = Path(os.environ.get("MPT_HOME", "mpt-runtime"))
    videos = load_validated_videos(home)
    seo_records = load_seo_manifest()

    # A reused topic must never be published twice. Private QA uploads are
    # deliberately excluded so a draft can be checked without consuming a topic.
    if scheduled or requested_privacy == "public":
        topics = [str(record.get("topic", "")).strip() for record in seo_records]
        try:
            ensure_new_topics(home / "state", topics)
        except RuntimeError as exc:
            raise SystemExit(str(exc))

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
    output_path = Path("youtube_scheduled_upload_results.json" if scheduled else f"youtube_{privacy}_upload_results.json")
    for index, (video_path, record) in enumerate(zip(videos, seo_records), start=1):
        metadata = record["metadata"]
        description = metadata["description"].strip()
        hashtags = [str(tag).strip().lstrip("#") for tag in metadata.get("hashtags", []) if str(tag).strip()]
        if hashtags:
            description += "\n\n" + " ".join("#" + tag for tag in hashtags[:3])
        tags = [str(tag).strip() for tag in metadata.get("tags", []) if str(tag).strip()][:15]
        publish_at = (first_publish_at + timedelta(hours=3 * (index - 1))) if scheduled else None
        body = {
            "snippet": {
                "title": metadata["title"][:100],
                "description": description[:5000],
                "tags": tags,
                "categoryId": "27",
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
                **({"publishAt": publish_at.isoformat(timespec="seconds").replace("+00:00", "Z")} if publish_at else {}),
            },
        }
        media = MediaFileUpload(str(video_path), mimetype="video/mp4",
                                chunksize=8 * 1024 * 1024, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"{privacy.upper()} upload {index}/{EXPECTED_COUNT}: {int(status.progress() * 100)}%")

        video_id = response.get("id")
        if not video_id:
            raise SystemExit(f"YouTube returned no video ID for upload {index}; upload cannot be confirmed.")
        result = {
            "index": index,
            "file": video_path.name,
            "video_id": video_id,
            "privacy": "scheduled" if scheduled else privacy,
            **({"publish_at_utc": publish_at.isoformat(timespec="seconds").replace("+00:00", "Z")} if publish_at else {}),
            "seo_source": record.get("metadata_source", "unknown"),
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }
        results.append(result)
        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        if scheduled or requested_privacy == "public":
            record_published_topic(home / "state", str(record["topic"]).strip())
        print(f"{privacy.upper()}_UPLOAD_SUCCEEDED {index}/{EXPECTED_COUNT}: {video_id}")

    if len(results) != EXPECTED_COUNT:
        raise SystemExit(f"Only {len(results)} of {EXPECTED_COUNT} uploads completed.")
    print(f"ALL_{EXPECTED_COUNT}_SCHEDULED_UPLOADS_SUCCEEDED" if scheduled else f"ALL_{EXPECTED_COUNT}_{privacy.upper()}_UPLOADS_SUCCEEDED")
    print(f"All {EXPECTED_COUNT} videos were scheduled as private uploads with future public release times." if scheduled else f"All {EXPECTED_COUNT} videos were uploaded with privacy={privacy}.")


if __name__ == "__main__":
    try:
        main()
    except HttpError as error:
        print(f"YouTube API returned HTTP {error.resp.status}.", file=sys.stderr)
        print(error.content.decode("utf-8", errors="replace")[:3000], file=sys.stderr)
        raise SystemExit(1)
