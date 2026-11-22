#!/usr/bin/env python3
"""Fail-closed technical and Persian-caption validation for a long-form documentary."""
import argparse, json, re, subprocess
from pathlib import Path
SRT_TIME = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})$")
def parse_srt(path: Path):
    text=path.read_text(encoding="utf-8-sig").strip()
    if not text: raise ValueError("Persian subtitle file is empty.")
    cues=[]; previous_end=-1
    for block in re.split(r"\n\s*\n",text):
        lines=block.splitlines()
        if len(lines)<3 or not lines[0].strip().isdigit(): raise ValueError("Malformed SRT cue.")
        match=SRT_TIME.match(lines[1].strip())
        if not match: raise ValueError("Malformed SRT timestamp.")
        v=[int(x) for x in match.groups()]
        start=(((v[0]*60+v[1])*60+v[2])*1000+v[3]); end=(((v[4]*60+v[5])*60+v[6])*1000+v[7])
        caption=" ".join(lines[2:]).strip()
        if end<=start or start<previous_end or not caption: raise ValueError("SRT cues must be non-empty and ordered without overlap.")
        if not any(0x0600<=ord(ch)<=0x06ff for ch in caption): raise ValueError("Subtitles must contain Persian-script text.")
        previous_end=end; cues.append({"start_ms":start,"end_ms":end,"text":caption})
    if len(cues)<3: raise ValueError("At least three Persian subtitle cues are required.")
    return cues
def inspect_documentary(path: Path,min_duration_seconds: int,subtitles=None):
    if not path.is_file() or path.stat().st_size<500_000: raise ValueError(f"Documentary file is missing or suspiciously small: {path}")
    result=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],capture_output=True,text=True,check=True)
    info=json.loads(result.stdout); streams=info.get("streams",[])
    video=next((s for s in streams if s.get("codec_type")=="video"),None)
    audio=next((s for s in streams if s.get("codec_type")=="audio"),None)
    if not video or not audio: raise ValueError("Final documentary must contain both video and audio streams.")
    width,height=int(video.get("width",0)),int(video.get("height",0))
    if width<1280 or height<720 or abs(width/height-16/9)>0.025: raise ValueError(f"Documentary must be at least 1280x720 in 16:9; got {width}x{height}.")
    duration=float(info.get("format",{}).get("duration",0))
    if duration<min_duration_seconds: raise ValueError(f"Documentary duration {duration:.1f}s is below the {min_duration_seconds}s minimum.")
    cues=parse_srt(subtitles) if subtitles else []
    if cues and cues[-1]["end_ms"]>(duration+1)*1000: raise ValueError("Persian subtitles extend beyond the final video duration.")
    return {"file":str(path),"duration_seconds":round(duration,2),"resolution":f"{width}x{height}","video_codec":video.get("codec_name"),"audio_codec":audio.get("codec_name"),"subtitle_cues":len(cues),"size_mb":round(path.stat().st_size/1_000_000,2),"status":"passed"}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--min-duration-seconds",type=int,default=600); p.add_argument("--subtitles"); p.add_argument("--report",default="documentary_quality_report.json"); a=p.parse_args()
    if a.min_duration_seconds<60: raise SystemExit("Minimum duration must be at least 60 seconds.")
    try: report=inspect_documentary(Path(a.input),a.min_duration_seconds,Path(a.subtitles) if a.subtitles else None)
    except (OSError,ValueError,subprocess.CalledProcessError,json.JSONDecodeError) as exc: raise SystemExit(f"DOCUMENTARY_QUALITY_GATE_FAILED: {exc}") from exc
    Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("DOCUMENTARY_QUALITY_GATE_PASSED "+json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()
