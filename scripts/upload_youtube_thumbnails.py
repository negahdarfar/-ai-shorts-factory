#!/usr/bin/env python3
"""Upload JPEG/PNG thumbnails to explicitly mapped YouTube video IDs."""
import argparse, json, os, sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES=["https://www.googleapis.com/auth/youtube.upload"]
def main():
    p=argparse.ArgumentParser(); p.add_argument("--manifest",default="youtube_thumbnail_manifest.json"); p.add_argument("--dry-run",action="store_true"); a=p.parse_args()
    rows=json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    if not isinstance(rows,list) or not rows: raise SystemExit("Manifest must be a non-empty JSON list.")
    seen=set()
    for row in rows:
      vid=str(row.get("video_id","")).strip(); path=Path(row.get("image_path","")).resolve()
      if not vid or vid in seen: raise SystemExit("Each row requires a unique video_id.")
      seen.add(vid)
      if not path.is_file() or path.suffix.lower() not in (".jpg",".jpeg",".png"): raise SystemExit(f"Missing or unsupported thumbnail: {path}")
      if path.stat().st_size>2_000_000: raise SystemExit(f"Thumbnail exceeds 2 MB: {path}")
    if a.dry_run:
      print(f"DRY_RUN_OK: {len(rows)} thumbnails mapped; no uploads.")
      return
    names=("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN")
    missing=[x for x in names if not os.getenv(x,"").strip()]
    if missing: raise SystemExit("Missing environment variables: "+", ".join(missing))
    creds=Credentials(None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"].strip(),token_uri="https://oauth2.googleapis.com/token",
      client_id=os.environ["YOUTUBE_CLIENT_ID"].strip(),client_secret=os.environ["YOUTUBE_CLIENT_SECRET"].strip(),scopes=SCOPES)
    creds.refresh(Request()); yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    for row in rows:
      path=Path(row["image_path"]).resolve()
      media=MediaFileUpload(str(path),mimetype="image/png" if path.suffix.lower()==".png" else "image/jpeg",resumable=False)
      yt.thumbnails().set(videoId=row["video_id"],media_body=media).execute()
      print(f"THUMBNAIL_UPLOADED {row['video_id']}")
if __name__=="__main__":
  try: main()
  except HttpError as e: print(f"YouTube API error HTTP {e.resp.status}",file=sys.stderr); raise SystemExit(1)
