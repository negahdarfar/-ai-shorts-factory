#!/usr/bin/env python3
"""Collect candidate links from configured RSS/Atom feeds; never verify claims."""
from __future__ import annotations
import argparse, json, re, socket, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
MAX_FEED_BYTES = 2_000_000
USER_AGENT = "KoroushLongformResearchBot/1.0 (+RSS metadata discovery)"
class FeedError(ValueError): pass
def safe_feed_url(value):
    p=urlparse(value); host=(p.hostname or "").lower()
    if p.scheme!="https" or not host or p.username or p.password: raise FeedError("Feed URL must be HTTPS and contain no credentials.")
    if host in {"localhost","localhost.localdomain"} or host.endswith(".local"): raise FeedError("Local feed hosts are not allowed.")
    try: socket.inet_aton(host)
    except OSError: pass
    else: raise FeedError("IP-literal feed hosts are not allowed.")
    return value
def node_text(node,names):
    for name in names:
        found=node.find(name)
        if found is not None and found.text: return re.sub(r"\s+"," ",found.text).strip()
    return ""
def entry_date(raw):
    if not raw: return None
    try:
        parsed=parsedate_to_datetime(raw)
        if parsed.tzinfo is None: parsed=parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).date().isoformat()
    except (TypeError,ValueError,OverflowError):
        try: return datetime.fromisoformat(raw.replace("Z","+00:00")).date().isoformat()
        except ValueError: return None
def parse_feed(payload,feed_url,publisher,topic,limit=30):
    try: root=ET.fromstring(payload)
    except ET.ParseError as exc: raise FeedError(f"Invalid RSS/Atom XML: {exc}") from exc
    terms=[x.lower() for x in re.findall(r"[\w-]{3,}",topic)]
    entries=root.findall(".//item")+root.findall(".//{http://www.w3.org/2005/Atom}entry")
    rows=[]
    for node in entries:
        title=node_text(node,("title","{http://www.w3.org/2005/Atom}title"))
        link=node_text(node,("link","{http://www.w3.org/2005/Atom}link"))
        atom_link=node.find("{http://www.w3.org/2005/Atom}link")
        if not link and atom_link is not None: link=atom_link.attrib.get("href","")
        summary=node_text(node,("description","summary","{http://www.w3.org/2005/Atom}summary"))
        published=node_text(node,("pubDate","published","updated","{http://www.w3.org/2005/Atom}published","{http://www.w3.org/2005/Atom}updated"))
        if not title or not link or urlparse(link).scheme!="https": continue
        haystack=(title+" "+summary).lower(); score=sum(term in haystack for term in terms)
        if terms and score==0: continue
        rows.append({"title":title[:500],"url":link,"publisher":publisher,"feed_url":feed_url,"published_at":entry_date(published),"topic_match_score":score,"discovery_only":True,"editorial_status":"needs_source_reading_and_review"})
    rows.sort(key=lambda x:(-x["topic_match_score"],x["published_at"] or ""))
    return rows[:limit]
def collect(feeds_path,topic,output_path,timeout=15,limit_per_feed=30):
    try: config=json.loads(Path(feeds_path).read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise FeedError(f"Cannot read feed configuration: {exc}") from exc
    feeds=config.get("feeds") if isinstance(config,dict) else None
    if not isinstance(feeds,list): raise FeedError("Feed configuration must contain a feeds array.")
    rows=[]; errors=[]; seen=set()
    for index,feed in enumerate(feeds):
        if not isinstance(feed,dict) or not feed.get("url") or not feed.get("publisher"):
            errors.append(f"Feed {index+1}: requires url and publisher."); continue
        try:
            url=safe_feed_url(str(feed["url"]))
            request=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml"})
            with urllib.request.urlopen(request,timeout=timeout) as response: payload=response.read(MAX_FEED_BYTES+1)
            if len(payload)>MAX_FEED_BYTES: raise FeedError("Feed exceeds 2 MB safety limit.")
            for row in parse_feed(payload,url,str(feed["publisher"]),topic,limit_per_feed):
                if row["url"] not in seen: seen.add(row["url"]); rows.append(row)
        except (FeedError,urllib.error.URLError,TimeoutError,OSError) as exc: errors.append(f"{feed.get('publisher','unknown')}: {exc}")
    result={"schema_version":1,"topic":topic,"collected_at":datetime.now(timezone.utc).isoformat(),"candidate_count":len(rows),"candidates":rows,"feed_errors":errors,"warning":"Discovery metadata only. Read each source and verify claims before adding it to research.json."}
    target=Path(output_path); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--feeds",required=True); parser.add_argument("--topic",required=True); parser.add_argument("--output",default="longform-output/research-candidates.json"); parser.add_argument("--timeout",type=int,default=15); parser.add_argument("--limit-per-feed",type=int,default=30); args=parser.parse_args()
    if not 1<=args.timeout<=60 or not 1<=args.limit_per_feed<=100: raise SystemExit("Timeout must be 1–60 seconds and limit-per-feed 1–100.")
    try: result=collect(args.feeds,args.topic,args.output,args.timeout,args.limit_per_feed)
    except FeedError as exc: raise SystemExit(f"RESEARCH_DISCOVERY_FAILED: {exc}") from exc
    print(f"RESEARCH_CANDIDATES_COLLECTED {result['candidate_count']}")
    if result["feed_errors"]: print(f"FEED_WARNINGS {len(result['feed_errors'])}")
if __name__=="__main__": main()
