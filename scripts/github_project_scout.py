#!/usr/bin/env python3
"""Discover relevant public GitHub repositories; read-only, no token required.

Uses GitHub's unauthenticated repository search API with conservative request
limits. Results are candidates for human review, never auto-installed or executed.
"""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com/search/repositories"
UA = "KoroushOpenSourceScout/1.0"
SEARCHES = {
    "llm": "llm language:Python",
    "text_to_video": '"text to video" language:Python',
    "video_generation": '"video generation" language:Python',
    "image_generation": '"image generation" language:Python',
    "text_to_speech": '"text to speech" language:Python',
    "youtube_automation": '"youtube automation" language:Python',
}
