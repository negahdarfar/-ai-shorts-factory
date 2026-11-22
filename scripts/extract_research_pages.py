#!/usr/bin/env python3
"""Fetch and extract readable text from RSS-discovered public pages.

Extracts bounded page text for editorial review. It does not fact-check, bypass
paywalls, execute JavaScript, or automatically promote text into verified claims.
"""
from __future__ import annotations
import argparse, ipaddress, json, re, socket, urllib.error, urllib.parse, urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from datetime import datetime, timezone
from pathlib import Path

MAX_PAGE_BYTES=1_500_000
MAX_TEXT_CHARS=30_000
USER_AGENT="KoroushLongformResearchBot/1.0"

class ExtractionError(ValueError): pass

def validate_public_url(url):
    p=urllib.parse.urlparse(url)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        raise ExtractionError("Only credential-free HTTPS URLs are allowed.")
    host=p.hostname
    if host.lower() in {"localhost","localhost.localdomain"} or host.lower().endswith(".local"):
        raise ExtractionError("Local hosts are blocked.")
    try:
        addresses={x[4][0] for x in socket.getaddrinfo(host,None)}
    except socket.gaierror as exc:
        raise ExtractionError(f"DNS lookup failed: {exc}") from exc
    if not addresses:
        raise ExtractionError("Hostname did not resolve.")
    for address in addresses:
        ip=ipaddress.ip_address(address)
        if not ip.is_global:
            raise ExtractionError("Private, loopback, link-local, or reserved IP destinations are blocked.")
    return url

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        validate_public_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

class TextExtractor(HTMLParser):
    SKIP={"script","style","noscript","svg","nav","footer","header","form","aside"}
    BLOCK={"p","div","article","section","h1","h2","h3","h4","li","blockquote","br"}
    def __init__(self):
        super().__init__(convert_charrefs=True); self.skip=0; self.parts=[]; self.title=[]; self.in_title=False
        self.description=""; self.canonical=""
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in self.SKIP: self.skip+=1
        if tag=="title": self.in_title=True
        if tag=="meta" and a.get("name","").lower() in {"description","og:description"}:
            self.description=self.description or a.get("content","")
        if tag=="link" and "canonical" in a.get("rel","").lower(): self.canonical=a.get("href","")
        if tag in self.BLOCK and self.skip==0: self.parts.append("\n")
    def handle_endtag(self,tag):
        if tag in self.SKIP and self.skip: self.skip-=1
        if tag=="title": self.in_title=False
        if tag in self.BLOCK and self.skip==0: self.parts.append("\n")
    def handle_data(self,data):
        if self.in_title: self.title.append(data)
        if self.skip==0: self.parts.append(data)
    def result(self):
        text=re.sub(r"[ \t]+"," ","".join(self.parts))
        text=re.sub(r"\n\s*\n+","\n\n",text).strip()
        return {"page_title":re.sub(r"\s+"," ","".join(self.title)).strip()[:500],
            "meta_description":self.description[:1000],"canonical_url":self.canonical,
            "extracted_text":text[:MAX_TEXT_CHARS],"truncated":len(text)>MAX_TEXT_CHARS}

def fetch_page(url,timeout=15):
    validate_public_url(url)
    opener=urllib.request.build_opener(SafeRedirect())
    request=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/html,application/xhtml+xml"})
    with opener.open(request,timeout=timeout) as response:
        final=response.geturl(); validate_public_url(final)
        content_type=response.headers.get_content_type()
        if content_type not in {"text/html","application/xhtml+xml"}:
            raise ExtractionError(f"Unsupported content type: {content_type}")
        payload=response.read(MAX_PAGE_BYTES+1)
    if len(payload)>MAX_PAGE_BYTES: raise ExtractionError("Page exceeds 1.5 MB safety limit.")
    charset="utf-8"
    try:
        charset=response.headers.get_content_charset() or "utf-8"
    except Exception: pass
    html=payload.decode(charset,errors="replace")
    parser=TextExtractor(); parser.feed(html); parser.close()
    data=parser.result()
    if not data["extracted_text"]: raise ExtractionError("No readable page text extracted.")
    data.update({"requested_url":url,"final_url":final,"content_type":content_type,
        "fetched_at":datetime.now(timezone.utc).isoformat(),"extraction_status":"needs_editorial_review",
        "fact_checked":False})
    return data

def extract_candidates(input_path,output_path,timeout=15,max_pages=20):
    try: raw=json.loads(Path(input_path).read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise ExtractionError(f"Cannot read candidate file: {exc}") from exc
    candidates=raw.get("candidates") if isinstance(raw,dict) else None
    if not isinstance(candidates,list): raise ExtractionError("Candidate input must contain a candidates array.")
    results=[]
    for item in candidates[:max_pages]:
        if not isinstance(item,dict) or not item.get("url"): continue
        record={k:item.get(k) for k in ("title","publisher","published_at","topic_match_score","url")}
        try: record.update(fetch_page(item["url"],timeout))
        except (ExtractionError,urllib.error.URLError,TimeoutError,OSError) as exc:
            record.update({"extraction_status":"failed","error":str(exc),"fact_checked":False})
        results.append(record)
    output={"schema_version":1,"topic":raw.get("topic",""),"candidate_count":len(candidates),
        "processed_count":len(results),"pages":results,
        "warning":"Extracted text is unverified source material. Review context, dates, authorship, and primary evidence before citing claims."}
    target=Path(output_path); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return output

def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",default="longform-output/research-extracts.json")
    p.add_argument("--timeout",type=int,default=15); p.add_argument("--max-pages",type=int,default=20); a=p.parse_args()
    if not 1<=a.timeout<=60 or not 1<=a.max_pages<=50: raise SystemExit("timeout 1-60 and max-pages 1-50 required")
    try: r=extract_candidates(a.input,a.output,a.timeout,a.max_pages)
    except ExtractionError as exc: raise SystemExit(f"RESEARCH_EXTRACTION_FAILED: {exc}") from exc
    print(f"RESEARCH_PAGES_EXTRACTED {sum(x.get('extraction_status')!='failed' for x in r['pages'])}/{r['processed_count']}")
if __name__=="__main__": main()
