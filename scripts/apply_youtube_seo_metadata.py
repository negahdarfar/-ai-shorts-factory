#!/usr/bin/env python3
"""Apply reviewed SEO metadata to explicitly mapped YouTube video IDs; never changes privacy."""
import argparse, json, os, sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES=["https://www.googleapis.com/auth/youtube"]
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",default="youtube_metadata_upload_manifest.json")
    p.add_argument("--dry-run",action="store_true")
    a=p.parse_args()
    data=json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    if not isinstance(data,list) or not data: raise SystemExit("Manifest must be a non-empty list.")
    seen=set()
    for row in data:
        vid=str(row.get("video_id","")).strip()
        meta=row.get("metadata",{})
        if not vid or vid in seen: raise SystemExit("Each row needs a unique explicit video_id.")
        seen.add(vid)
        title=str(meta.get("title","")).strip(); desc=str(meta.get("description","")).strip()
        if not title or len(title)>100 or not desc or len(desc.encode("utf-8"))>5000:
            raise SystemExit(f"Invalid title/description for video {vid}.")
        if not isinstance(meta.get("tags",[]),list) or len(meta.get("tags",[]))>500:
            raise SystemExit(f"Invalid tags for video {vid}.")
    if a.dry_run:
        print(f"DRY_RUN_OK: {len(data)} explicitly mapped video metadata records; no API writes.")
        return
    required=("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN")
    missing=[x for x in required if not os.getenv(x,"").strip()]
    if missing: raise SystemExit("Missing environment variables: "+", ".join(missing))
    creds=Credentials(None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"].strip(),
        token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YOUTUBE_CLIENT_ID"].strip(),
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"].strip(),scopes=SCOPES)
    creds.refresh(Request()); yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    for row in data:
        meta=row["metadata"]; vid=row["video_id"]
        current=yt.videos().list(part="snippet",id=vid).execute()
        items=current.get("items",[])
        if not items: raise SystemExit(f"Video ID not found or inaccessible: {vid}")
        old=items[0]["snippet"]
        body={"id":vid,"snippet":{"title":meta["title"],"description":meta["description"],
            "categoryId":old.get("categoryId","22"),"tags":meta.get("tags",[])[:500],
            "defaultLanguage":row.get("language","en")}}
        yt.videos().update(part="snippet",body=body).execute()
        print(f"SEO_METADATA_APPLIED {vid}")
    print("Metadata updated. Existing privacy settings were not modified.")
if __name__=="__main__":
    try: main()
    except HttpError as e:
        print(f"YouTube API error: HTTP {e.resp.status}",file=sys.stderr); raise SystemExit(1)
