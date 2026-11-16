#!/usr/bin/env python3
"""Validate the stored YouTube OAuth refresh token without uploading anything."""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    names = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [name for name in names if not os.environ.get(name, "").strip()]
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
    print("YOUTUBE_OAUTH_REFRESH_SUCCEEDED")
    print("Token refresh was validated. No YouTube video was uploaded.")

if __name__ == "__main__":
    main()
