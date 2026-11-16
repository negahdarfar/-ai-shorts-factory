#!/usr/bin/env python3
"""Fetch read-only channel analytics; requires a refresh token consented for yt-analytics.readonly."""
import argparse, json, os, sys
from datetime import date, timedelta
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPE="https://www.googleapis.com/auth/yt-analytics.readonly"
def main():
    p=argparse.ArgumentParser(); p.add_argument("--days",type=int,default=28); p.add_argument("--output",default="youtube_analytics.json"); a=p.parse_args()
    if not 1<=a.days<=365: raise SystemExit("--days must be from 1 to 365.")
    required=("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN")
    missing=[x for x in required if not os.getenv(x,"").strip()]
    if missing: raise SystemExit("Missing environment variables: "+", ".join(missing))
    creds=Credentials(None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"].strip(),
      token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YOUTUBE_CLIENT_ID"].strip(),
      client_secret=os.environ["YOUTUBE_CLIENT_SECRET"].strip(),scopes=[SCOPE])
    try: creds.refresh(Request())
    except Exception as e:
      raise SystemExit("OAuth refresh failed. Re-authorize the channel and grant yt-analytics.readonly; the existing upload-only token cannot be expanded in place. "+str(e))
    api=build("youtubeAnalytics","v2",credentials=creds,cache_discovery=False)
    end=date.today()-timedelta(days=2); start=end-timedelta(days=a.days-1)
    reports={}
    queries={
      "engagement":{"metrics":"views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained","dimensions":"day"},
      "impressions":{"metrics":"impressions,impressionClickThroughRate","dimensions":"day"}
    }
    for name,q in queries.items():
      try:
        result=api.reports().query(ids="channel==MINE",startDate=start.isoformat(),endDate=end.isoformat(),
          metrics=q["metrics"],dimensions=q["dimensions"],sort="day").execute()
        reports[name]={"columnHeaders":result.get("columnHeaders",[]),"rows":result.get("rows",[])}
      except HttpError as e:
        reports[name]={"unavailable":f"HTTP {e.resp.status}; metric combination may not be supported for this channel."}
    payload={"start_date":start.isoformat(),"end_date":end.isoformat(),"reports":reports,
      "note":"Analytics are descriptive, not causal proof. Compare like-for-like formats and publication ages."}
    Path(a.output).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"YOUTUBE_ANALYTICS_SAVED {a.output}")
if __name__=="__main__":
  try: main()
  except Exception as e: print(f"Analytics failed: {e}",file=sys.stderr); raise SystemExit(1)
