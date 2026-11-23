#!/usr/bin/env python3
"""Standalone, license-aware discovery and Shorts renderer."""
from __future__ import annotations
import argparse, hashlib, html, json, os, re, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

API = "https://commons.wikimedia.org/w/api.php"
UA = "KoroushViralFactory/1.0 (standalone workflow)"
TERMS = ["science video", "space video", "wildlife video", "nature video",
         "ocean video", "technology video", "history video", "landscape video"]
LICENSES = ("cc0", "cc by", "public domain")
MAX_BYTES = 500 * 1024 * 1024
HOOKS = {"secret","shocking","amazing","never","impossible","truth","mistake",
         "discovered","incredible","surprising","dangerous","why","how",
         "finally","unexpected","revealed","first time"}

def get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))

def clean(value: Any) -> str:
    value = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", value)).strip()

def allowed_license(name: str) -> bool:
    text = clean(name).lower().replace("_", " ").replace("-", " ")
    if any(x in text for x in ("noncommercial","non commercial","no derivatives")) or re.search(r"\bnc\b|\bnd\b", text):
        return False
    return any(x in text for x in LICENSES)

def commons_search(term: str) -> list[dict[str, Any]]:
    params = {"action":"query","format":"json","generator":"search","gsrsearch":term,
              "gsrnamespace":6,"gsrlimit":40,"prop":"imageinfo",
              "iiprop":"url|size|mime|extmetadata"}
    data = get_json(API + "?" + urllib.parse.urlencode(params))
    rows = []
    for page in data.get("query", {}).get("pages", {}).values():
        infos = page.get("imageinfo") or []
        if not infos: continue
        info = infos[0]
        if not str(info.get("mime","")).startswith("video/"): continue
        size = int(info.get("size") or 0)
        if size < 1024*1024 or size > MAX_BYTES: continue
        meta = info.get("extmetadata") or {}
        def m(key: str) -> str:
            return clean((meta.get(key) or {}).get("value",""))
        license_name, license_url = m("LicenseShortName"), m("LicenseUrl")
        url = info.get("url","")
        if not allowed_license(license_name) or not url.startswith("https://upload.wikimedia.org/"):
            continue
        title = page.get("title","")
        rows.append({"title":title,"download_url":url,
          "source_page":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_")),
          "mime":info.get("mime"),"size_bytes":size,"license":license_name,
          "license_url":license_url,"artist":m("Artist"),"credit":m("Credit"),
          "description":m("ImageDescription"),"source":"Wikimedia Commons"})
    return rows

def youtube_trends() -> list[dict[str, Any]]:
    key = os.getenv("YOUTUBE_API_KEY","").strip()
    if not key:
        print("YOUTUBE_API_KEY absent: skipping optional YouTube trend metadata.")
        return []
    url = "https://www.googleapis.com/youtube/v3/videos?"+urllib.parse.urlencode({
      "part":"snippet,statistics","chart":"mostPopular",
      "regionCode":os.getenv("VIRAL_REGION","US"),"maxResults":"25","key":key})
    data = get_json(url)
    rows=[]
    for item in data.get("items",[]):
        sn, st = item.get("snippet",{}), item.get("statistics",{})
        rows.append({"video_id":item.get("id"),"title":sn.get("title"),
          "channel":sn.get("channelTitle"),"published_at":sn.get("publishedAt"),
          "views":int(st.get("viewCount",0)),"likes":int(st.get("likeCount",0)),
          "url":"https://www.youtube.com/watch?v="+str(item.get("id")),
          "note":"Metadata only; not downloaded or republished."})
    return sorted(rows,key=lambda x:x["views"],reverse=True)

def discover(out: Path) -> None:
    out.mkdir(parents=True,exist_ok=True)
    unique={}
    for term in TERMS:
        print("Commons search:",term)
        try:
            for row in commons_search(term): unique[row["download_url"]]=row
        except Exception as exc: print("Search warning:",exc)
        time.sleep(.35)
    candidates=sorted(unique.values(),key=lambda x:x["size_bytes"])
    (out/"commons_candidates.json").write_text(json.dumps(candidates,ensure_ascii=False,indent=2),encoding="utf-8")
    trends=youtube_trends()
    (out/"youtube_trends.json").write_text(json.dumps(trends,ensure_ascii=False,indent=2),encoding="utf-8")
    report={"commons_candidates":len(candidates),"youtube_trend_items":len(trends),
      "youtube_api_enabled":bool(os.getenv("YOUTUBE_API_KEY")),
      "generated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    (out/"discovery_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    if not candidates and not trends: raise RuntimeError("No discovery results; check network/API access.")

def download_candidate(path: Path,index: int,target: Path) -> dict[str,Any]:
    rows=json.loads(path.read_text(encoding="utf-8"))
    if index<0 or index>=len(rows): raise IndexError("Candidate index out of range; inspect commons_candidates.json.")
    item=rows[index]
    if not allowed_license(item.get("license","")): raise ValueError("Candidate license is not allowed.")
    parsed=urllib.parse.urlparse(item.get("download_url",""))
    if parsed.scheme!="https" or parsed.hostname!="upload.wikimedia.org":
        raise ValueError("Refusing download from non-Wikimedia host.")
    req=urllib.request.Request(item["download_url"],headers={"User-Agent":UA})
    target.parent.mkdir(parents=True,exist_ok=True); temp=target.with_suffix(".part")
    total=0
    try:
        with urllib.request.urlopen(req,timeout=120) as response,temp.open("wb") as out_file:
            ctype=response.headers.get("Content-Type","")
            if not (ctype.startswith("video/") or "octet-stream" in ctype):
                raise ValueError("Unexpected source content type.")
            while True:
                chunk=response.read(1024*1024)
                if not chunk: break
                total+=len(chunk)
                if total>MAX_BYTES: raise ValueError("Source exceeds 500 MiB.")
                out_file.write(chunk)
        if total==0: raise ValueError("Empty download.")
        temp.replace(target)
    finally:
        if temp.exists(): temp.unlink()
    item["downloaded_file"]=str(target); item["downloaded_bytes"]=total
    (target.parent/"source_attribution.json").write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding="utf-8")
    return item

def probe(path: Path) -> float:
    result=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
      "-of","default=noprint_wrappers=1:nokey=1",str(path)],capture_output=True,text=True,check=True)
    return float(result.stdout.strip())

def transcribe(path: Path,model_name: str) -> list[dict[str,Any]]:
    from faster_whisper import WhisperModel
    model=WhisperModel(model_name,device="cpu",compute_type="int8")
    segments,info=model.transcribe(str(path),beam_size=3,vad_filter=True)
    if getattr(info,"language",None)!="en":
        raise ValueError(f"Viral Factory accepts English-source audio only; Whisper detected {getattr(info,'language','unknown')}.")
    return [{"start":round(s.start,2),"end":round(s.end,2),"text":s.text.strip()}
            for s in segments if s.text.strip()]

def srt_timestamp(seconds: float) -> str:
    millis=max(0,int(round(seconds*1000)))
    hours,remain=divmod(millis,3600000)
    minutes,remain=divmod(remain,60000)
    whole,ms=divmod(remain,1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d},{ms:03d}"

def write_clip_srt(segments: list[dict[str,Any]],clip: dict[str,Any],target: Path) -> int:
    rows=[]
    for segment in segments:
        start=max(float(clip["start"]),float(segment["start"]))
        end=min(float(clip["end"]),float(segment["end"]))
        text=clean(segment.get("text",""))
        if end>start and text:
            rows.append((start-float(clip["start"]),end-float(clip["start"]),text))
    if len(rows)<3:
        raise ValueError("Selected clip has fewer than three usable English subtitle cues.")
    payload="\n\n".join(
        f"{i}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{text}"
        for i,(start,end,text) in enumerate(rows,1)
    )+"\n"
    target.write_text(payload,encoding="utf-8")
    return len(rows)

def burn_persian_subtitles(video: Path,srt: Path) -> None:
    if not srt.is_file() or not srt.stat().st_size:
        raise ValueError("Persian SRT is missing; refusing to keep an uncaptioned viral clip.")
    text=srt.read_text(encoding="utf-8-sig")
    if not any(0x0600<=ord(ch)<=0x06ff for ch in text):
        raise ValueError("Persian subtitle file contains no Persian-script text.")
    escaped=str(srt.resolve()).replace("\\","\\\\").replace(":","\\:").replace("'","\\'")
    vf=f"subtitles='{escaped}':force_style='FontName=Noto Naskh Arabic,FontSize=30,Outline=2,Shadow=1,Alignment=2,MarginV=82,WrapStyle=2'"
    temp=video.with_name(video.stem+".fa-subtitled.mp4")
    subprocess.run(["ffmpeg","-y","-i",str(video),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","21","-c:a","copy","-movflags","+faststart",str(temp)],check=True)
    temp.replace(video)

def validate_viral_clip(video: Path,srt: Path) -> dict[str,Any]:
    result=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(video)],capture_output=True,text=True,check=True)
    info=json.loads(result.stdout)
    streams=info.get("streams",[])
    v=next((x for x in streams if x.get("codec_type")=="video"),None)
    a=next((x for x in streams if x.get("codec_type")=="audio"),None)
    if not v or not a: raise ValueError(f"Missing video or audio stream: {video}")
    width,height=int(v.get("width",0)),int(v.get("height",0))
    duration=float(info.get("format",{}).get("duration",0))
    if width<720 or height<1280 or abs(width/height-9/16)>0.025:
        raise ValueError(f"Viral clip is not valid vertical 9:16 media: {width}x{height}")
    if not 20<=duration<=58: raise ValueError(f"Viral clip duration must be 20-58 seconds, got {duration:.1f}.")
    if not srt.is_file() or not any(0x0600<=ord(ch)<=0x06ff for ch in srt.read_text(encoding="utf-8-sig")):
        raise ValueError("Persian SRT missing or invalid.")
    return {"file":video.name,"duration_seconds":round(duration,2),"resolution":f"{width}x{height}","subtitle_file":srt.name,"status":"passed"}

def score(text: str) -> float:
    lower=text.lower(); words=re.findall(r"\b\w+\b",lower)
    value=sum(2.5 for term in HOOKS if term in lower)
    value+=2 if "?" in text else 0
    value+=1 if "!" in text else 0
    value+=1 if re.search(r"\d",text) else 0
    value+=2 if 35<=len(words)<=115 else 0
    return round(value+min(len(set(words))/30,1.5),2)

def select(segments: list[dict[str,Any]],duration: float,limit: int) -> list[dict[str,Any]]:
    windows=[]
    for i,seg in enumerate(segments):
        start=float(seg["start"]); end=start; texts=[]
        for nxt in segments[i:]:
            if float(nxt["end"])-start>58: break
            end=float(nxt["end"]); texts.append(nxt["text"]); span=end-start
            if 20<=span<=58:
                text=" ".join(texts)
                windows.append({"start":round(start,2),"end":round(end,2),
                  "duration":round(span,2),"text":text,"score":score(text)})
    windows.sort(key=lambda x:x["score"],reverse=True)
    chosen=[]
    for candidate in windows:
        if all(candidate["end"]<=old["start"] or candidate["start"]>=old["end"] for old in chosen):
            chosen.append(candidate)
        if len(chosen)>=limit: break
    if not chosen and duration>=20:
        count=min(limit,int(duration//20))
        step=duration/count
        length=min(35.0,step)
        for i in range(count):
            start=i*step
            chosen.append({"start":round(start,2),"end":round(start+length,2),
              "duration":round(length,2),"text":"","score":0,"selection":"evenly-spaced fallback"})
    return chosen

def render(source: Path,clip: dict[str,Any],target: Path) -> None:
    target.parent.mkdir(parents=True,exist_ok=True)
    vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    subprocess.run(["ffmpeg","-y","-ss",str(clip["start"]),"-i",str(source),
      "-t",str(clip["duration"]),"-map","0:v:0","-map","0:a?","-vf",vf,
      "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac",
      "-b:a","128k","-movflags","+faststart",str(target)],check=True)

def process(index: int | str,out: Path,limit: int,model: str) -> None:
    candidates=out/"commons_candidates.json"
    if not candidates.exists(): raise FileNotFoundError("Run discover first.")
    candidate_rows=json.loads(candidates.read_text(encoding="utf-8"))
    used_path=out/"used_sources.json"
    if used_path.exists():
        used_value=json.loads(used_path.read_text(encoding="utf-8"))
        if not isinstance(used_value,list) or any(not isinstance(x,str) for x in used_value):
            raise ValueError("used_sources.json is malformed; refusing to reuse a source blindly.")
        used=set(used_value)
    else:
        used=set()
    if str(index).strip().lower()=="auto":
        index=next((i for i,row in enumerate(candidate_rows) if row.get("download_url") not in used),None)
        if index is None: raise RuntimeError("No unused licensed Commons source remains in this discovery batch.")
    else:
        index=int(index)
    source=out/"source.mp4"; attribution=download_candidate(candidates,index,source)
    duration=probe(source)
    if duration<20: raise ValueError("Source video is shorter than 20 seconds.")
    print("Transcribing with local Whisper model:",model)
    transcript=transcribe(source,model)
    (out/"transcript.json").write_text(json.dumps(transcript,ensure_ascii=False,indent=2),encoding="utf-8")
    clips=select(transcript,duration,limit)
    (out/"selected_clips.json").write_text(json.dumps(clips,ensure_ascii=False,indent=2),encoding="utf-8")
    if not os.getenv("GEMINI_API_KEY","").strip() and not os.getenv("AVALAI_API_KEY","").strip():
        raise RuntimeError("Configure AVALAI_API_KEY (free models only) or the existing GEMINI_API_KEY fallback; no uncaptioned clip will be released.")
    translator=Path(__file__).resolve().parents[1]/"scripts"/"translate_srt_to_persian.py"
    if not translator.is_file(): raise FileNotFoundError("Shared Persian SRT translator is missing.")
    quality=[]
    for n,clip in enumerate(clips,1):
        target=out/"shorts"/("viral_short_%02d.mp4"%n)
        en_srt=target.with_suffix(".en.srt")
        fa_srt=target.with_suffix(".fa.srt")
        render(source,clip,target)
        cue_count=write_clip_srt(transcript,clip,en_srt)
        subprocess.run([sys.executable,str(translator),"--input",str(en_srt),"--output",str(fa_srt),"--model",os.getenv("SEO_GEMINI_MODEL","gemini-2.5-flash")],check=True)
        burn_persian_subtitles(target,fa_srt)
        quality.append(validate_viral_clip(target,fa_srt))
        print(f"Rendered and validated Persian-subtitled clip {n}/{len(clips)} ({cue_count} cues):",target)
    (out/"viral_quality_report.json").write_text(json.dumps(quality,ensure_ascii=False,indent=2),encoding="utf-8")
    used.add(str(attribution.get("download_url","")))
    used_path.write_text(json.dumps(sorted(used),ensure_ascii=False,indent=2),encoding="utf-8")
    description=("Edited short from a Creative Commons-licensed source.\n\n"
      +"Source: "+attribution.get("source_page","")+"\n"
      +"Creator: "+(attribution.get("artist") or "Not stated")+"\n"
      +"Credit: "+(attribution.get("credit") or "See source page")+"\n"
      +"License: "+attribution.get("license","")+" "+attribution.get("license_url",""))
    (out/"publish_metadata.json").write_text(json.dumps({
      "title_prefix":attribution.get("title","Creative Commons video"),
      "description":description,"tags":["shorts","creativecommons","education"]},
      ensure_ascii=False,indent=2),encoding="utf-8")

def publish(out: Path,max_uploads: int) -> None:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    required=("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN")
    missing=[name for name in required if not os.getenv(name)]
    if missing: raise RuntimeError("Missing YouTube OAuth secrets: "+", ".join(missing))
    attribution_path=out/"source_attribution.json"
    if not attribution_path.is_file(): raise RuntimeError("Source attribution is missing; publication blocked.")
    attribution=json.loads(attribution_path.read_text(encoding="utf-8"))
    if not allowed_license(attribution.get("license","")): raise RuntimeError("Source licence is not on the approved allowlist.")
    creds=Credentials(token=None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
      token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YOUTUBE_CLIENT_ID"],
      client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],scopes=["https://www.googleapis.com/auth/youtube.upload"])
    creds.refresh(Request())
    if not creds.valid or not creds.token: raise RuntimeError("YouTube OAuth did not return a valid access token.")
    api=build("youtube","v3",credentials=creds,cache_discovery=False)
    meta=json.loads((out/"publish_metadata.json").read_text(encoding="utf-8"))
    files=sorted((out/"shorts").glob("*.mp4"))[:max_uploads]
    if not files: raise FileNotFoundError("No rendered Shorts found.")
    ledger_path=out/"upload_history.json"
    if ledger_path.exists():
        ledger=json.loads(ledger_path.read_text(encoding="utf-8"))
        if not isinstance(ledger,dict) or not isinstance(ledger.get("uploads"),dict):
            raise RuntimeError("Viral upload history is malformed; refusing to risk duplicate publication.")
    else:
        ledger={"schema_version":1,"uploads":{}}
    uploaded=[]
    for path in files:
        srt=path.with_suffix(".fa.srt")
        quality=validate_viral_clip(path,srt)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        key="public:"+digest
        previous=ledger["uploads"].get(key)
        if previous:
            if previous.get("status")=="pending":
                raise RuntimeError(f"Upload {path.name} is pending reconciliation; check YouTube Studio before retrying.")
            if previous.get("status")!="completed" or not previous.get("video_id"):
                raise RuntimeError(f"Invalid completed upload record for {path.name}.")
            uploaded.append(previous)
            print("Already uploaded; skipping duplicate:",previous.get("url"))
            continue
        pending={"status":"pending","mode":"public","sha256":digest,"file":path.name,
                 "source_page":attribution.get("source_page"),"license":attribution.get("license"),
                 "started_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"quality":quality}
        ledger["uploads"][key]=pending
        ledger_path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding="utf-8")
        body={"snippet":{"title":(meta["title_prefix"][:75]+" #Shorts")[:100],
          "description":meta["description"],"tags":meta.get("tags",[]),"categoryId":"27","defaultLanguage":"en"},
          "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False,"containsSyntheticMedia":False}}
        media=MediaFileUpload(str(path),mimetype="video/mp4",resumable=True)
        response=api.videos().insert(part="snippet,status",body=body,media_body=media,notifySubscribers=False).execute()
        video_id=response.get("id")
        if not video_id: raise RuntimeError("YouTube returned no video ID; pending ledger retained for reconciliation.")
        result={"file":path.name,"video_id":video_id,"sha256":digest,"privacy":"public",
                "source_page":attribution.get("source_page"),"license":attribution.get("license"),
                "url":"https://www.youtube.com/watch?v="+str(video_id)}
        ledger["uploads"][key]={**pending,"status":"completed","video_id":video_id,"url":result["url"],
                                "completed_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
        ledger_path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding="utf-8")
        uploaded.append(result)
        print("Upload confirmed:",result["url"])
    (out/"uploaded_videos.json").write_text(json.dumps(uploaded,ensure_ascii=False,indent=2),encoding="utf-8")

def main() -> None:
    parser=argparse.ArgumentParser(description="KOROUSH Viral Factory")
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("discover"); p.add_argument("--output-dir",type=Path,default=Path("viral_factory/work"))
    p=sub.add_parser("process"); p.add_argument("--candidate-index",type=str,default="auto")
    p.add_argument("--output-dir",type=Path,default=Path("viral_factory/work"))
    p.add_argument("--limit",type=int,default=4); p.add_argument("--model",default="tiny")
    p=sub.add_parser("publish"); p.add_argument("--output-dir",type=Path,default=Path("viral_factory/work"))
    p.add_argument("--max-uploads",type=int,default=4)
    args=parser.parse_args()
    if args.command=="discover": discover(args.output_dir)
    elif args.command=="process": process(args.candidate_index,args.output_dir,max(1,min(args.limit,8)),args.model)
    else: publish(args.output_dir,max(1,min(args.max_uploads,4)))

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("ERROR:",exc,file=sys.stderr); raise
