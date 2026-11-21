#!/usr/bin/env python3
"""Idempotent uploader for 4-10 validated YouTube Shorts.

Privacy is PRIVATE by default. PUBLIC publishing is possible only when the
workflow explicitly sets YOUTUBE_PRIVACY_STATUS=public and confirms it.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from topic_history import ensure_new_topics, record_published_topic
from upload_history import idempotency_key, load_upload_history, save_upload_history, sha256_file
from content_metadata import classify_hook, extract_hook

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
        raise SystemExit(f"Could not read the video quality report: {exc}") from exc
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
        topic = str(item.get("topic", "")).strip()
        if not topic:
            raise SystemExit(f"Quality report has no topic mapping for {relative_path!r}.")
        videos.append({"path": path, "topic": topic, "index": int(item.get("index", len(videos) + 1))})

    if len({item["path"].resolve() for item in videos}) != EXPECTED_COUNT:
        raise SystemExit(f"The validation report does not identify {EXPECTED_COUNT} distinct video files.")
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


def write_results(path: Path, results_by_index: dict[int, dict]) -> None:
    ordered = [results_by_index[index] for index in sorted(results_by_index)]
    path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    requested_privacy = os.environ.get("YOUTUBE_PRIVACY_STATUS", "private").strip().lower()
    scheduled = os.environ.get("YOUTUBE_SCHEDULED_PUBLISH", "NO").strip().upper() == "YES"
    if requested_privacy not in {"private", "public"}:
        raise SystemExit("YOUTUBE_PRIVACY_STATUS must be either private or public.")
    if requested_privacy == "public" and os.environ.get("CONFIRM_PUBLIC_PUBLISHING") != "YES":
        raise SystemExit("Public upload blocked: explicit workflow confirmation is missing.")

    privacy = "private" if scheduled else requested_privacy
    mode = "public" if scheduled or requested_privacy == "public" else "private"
    first_publish_at = None
    if scheduled:
        candidate = datetime.now(timezone.utc) + timedelta(minutes=60)
        first_publish_at = candidate.replace(minute=0, second=0, microsecond=0)
        if first_publish_at < candidate:
            first_publish_at += timedelta(hours=1)
        print(f"SCHEDULING_PUBLIC_SHORTS: count={EXPECTED_COUNT} | first slot {first_publish_at.isoformat()}")

    home = Path(os.environ.get("MPT_HOME", "mpt-runtime"))
    videos = load_validated_videos(home)
    seo_records = load_seo_manifest()
    state_dir = home / "state"
    history = load_upload_history(state_dir)
    output_path = Path("youtube_scheduled_upload_results.json" if scheduled else f"youtube_{privacy}_upload_results.json")

    prepared = []
    results_by_index = {}
    new_public_topics = []
    seo_by_topic = {str(record.get("topic", "")).strip().casefold(): record for record in seo_records}
    if len(seo_by_topic) != EXPECTED_COUNT:
        raise SystemExit("SEO manifest contains duplicate or missing topic names; refusing upload.")
    for video_item in videos:
        index = video_item["index"]
        video_path = video_item["path"]
        topic = video_item["topic"]
        record = seo_by_topic.get(topic.casefold())
        if record is None:
            raise SystemExit(f"No SEO metadata record matches rendered topic: {topic}")
        digest = sha256_file(video_path)
        ledger_key = idempotency_key(mode, digest)
        previous = history["uploads"].get(ledger_key)
        if previous:
            status = previous.get("status")
            if status == "pending":
                raise SystemExit(
                    f"UPLOAD_REQUIRES_RECONCILIATION: {video_path.name} has a pending {mode} upload. "
                    "Check YouTube Studio before clearing the pending ledger entry; do not blindly retry."
                )
            if status != "completed" or not isinstance(previous.get("result"), dict) or not previous["result"].get("video_id"):
                raise SystemExit(f"Upload ledger entry for {video_path.name} is invalid; refusing duplicate upload.")
            results_by_index[index] = previous["result"]
            print(f"UPLOAD_ALREADY_COMPLETED; skipping duplicate {mode} upload: {previous['result']['video_id']}")
            continue

        publish_at = (first_publish_at + timedelta(hours=3 * (index - 1))) if scheduled else None
        prepared.append((index, video_path, record, digest, ledger_key, publish_at))
        if mode == "public":
            new_public_topics.append(str(record.get("topic", "")).strip())

    if mode == "public" and new_public_topics:
        try:
            ensure_new_topics(state_dir, new_public_topics)
        except RuntimeError as exc:
            raise SystemExit(str(exc))

    if not prepared:
        write_results(output_path, results_by_index)
        print(f"ALL_{EXPECTED_COUNT}_{mode.upper()}_UPLOADS_ALREADY_COMPLETED; no duplicate uploads created.")
        return

    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        raise SystemExit("Missing GitHub Actions secrets: " + ", ".join(missing))

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
    for index, video_path, record, digest, ledger_key, publish_at in prepared:
        metadata = record["metadata"]
        description = metadata["description"].strip()
        hashtags = [str(tag).strip().lstrip("#") for tag in metadata.get("hashtags", []) if str(tag).strip()]
        if hashtags:
            description += "\n\n" + " ".join("#" + tag for tag in hashtags[:3])
        tags = [str(tag).strip() for tag in metadata.get("tags", []) if str(tag).strip()][:15]
        publish_at_text = publish_at.isoformat(timespec="seconds").replace("+00:00", "Z") if publish_at else None

        hook_text = extract_hook(record["video_script"])
        hook_type = classify_hook(hook_text)
        pending = {
            "mode": mode,
            "status": "pending",
            "sha256": digest,
            "file": video_path.name,
            "topic": str(record["topic"]).strip(),
            "title": metadata["title"][:100],
            "hook_text": hook_text,
            "hook_type": hook_type,
            "privacy": privacy,
            "scheduled": scheduled,
            "publish_at_utc": publish_at_text,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        history["uploads"][ledger_key] = pending
        save_upload_history(state_dir, history)

        body = {
            "snippet": {
                "title": metadata["title"][:100],
                "description": description[:5000],
                "tags": tags,
                "categoryId": "27",
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
                # Current factory visuals are licensed stock footage, not realistic synthetic scenes.
                # Revisit this flag if realistic AI-generated depictions are introduced.
                "containsSyntheticMedia": False,
                **({"publishAt": publish_at_text} if publish_at_text else {}),
            },
        }
        media = MediaFileUpload(
            str(video_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True
        )
        request = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media, notifySubscribers=False
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"{privacy.upper()} upload {index}/{EXPECTED_COUNT}: {int(status.progress() * 100)}%")

        video_id = response.get("id")
        if not video_id:
            raise SystemExit(f"YouTube returned no video ID for upload {index}; pending ledger retained for reconciliation.")

        result = {
            "index": index,
            "file": video_path.name,
            "sha256": digest,
            "topic": str(record["topic"]).strip(),
            "title": metadata["title"][:100],
            "hook_text": hook_text,
            "hook_type": hook_type,
            "video_id": video_id,
            "privacy": "scheduled" if scheduled else privacy,
            **({"publish_at_utc": publish_at_text} if publish_at_text else {}),
            "seo_source": record.get("metadata_source", "unknown"),
            "contains_synthetic_media": False,
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }
        history["uploads"][ledger_key] = {
            **pending,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "video_id": video_id,
            "url": result["url"],
            "result": result,
        }
        save_upload_history(state_dir, history)
        results_by_index[index] = result
        write_results(output_path, results_by_index)

        if mode == "public":
            record_published_topic(state_dir, str(record["topic"]).strip())
        print(f"{privacy.upper()}_UPLOAD_SUCCEEDED {index}/{EXPECTED_COUNT}: {video_id}")

    if len(results_by_index) != EXPECTED_COUNT:
        raise SystemExit(f"Only {len(results_by_index)} of {EXPECTED_COUNT} uploads are complete.")
    print(f"ALL_{EXPECTED_COUNT}_{mode.upper()}_UPLOADS_SUCCEEDED")
    print(
        f"Completed {EXPECTED_COUNT} {mode} upload records. "
        "Previously completed files were skipped using the SHA-256 upload ledger."
    )


if __name__ == "__main__":
    try:
        main()
    except HttpError as error:
        print(f"YouTube API returned HTTP {error.resp.status}.", file=sys.stderr)
        print(error.content.decode("utf-8", errors="replace")[:3000], file=sys.stderr)
        raise SystemExit(1)
