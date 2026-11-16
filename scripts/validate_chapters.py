#!/usr/bin/env python3
"""Validate YouTube chapter timestamps before adding them to a long-form description."""
import argparse,re
from pathlib import Path
def seconds(stamp):
    parts=stamp.split(":")
    if len(parts)==2: return int(parts[0])*60+int(parts[1])
    if len(parts)==3: return int(parts[0])*3600+int(parts[1])*60+int(parts[2])
    raise ValueError(stamp)
def main():
    p=argparse.ArgumentParser(); p.add_argument("file"); a=p.parse_args()
    text=Path(a.file).read_text(encoding="utf-8")
    rows=[]
    for line in text.splitlines():
      m=re.match(r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)\s*$",line)
      if m: rows.append((seconds(m.group(1)),m.group(2)))
    if len(rows)<3: raise SystemExit("YouTube chapters require at least 3 timestamped entries.")
    if rows[0][0]!=0: raise SystemExit("First chapter must start at 00:00.")
    if any(b[0]<=a[0] for a,b in zip(rows,rows[1:])): raise SystemExit("Chapter timestamps must be strictly increasing.")
    if any(not title.strip() for _,title in rows): raise SystemExit("Chapter titles cannot be empty.")
    print(f"CHAPTERS_VALIDATED {len(rows)} chapters.")
if __name__=="__main__": main()
