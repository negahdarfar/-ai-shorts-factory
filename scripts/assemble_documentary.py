#!/usr/bin/env python3
"""Assemble ordered video clips into a long-form MP4 and optionally add Persian SRT subtitles."""
import argparse, json, subprocess, tempfile
from pathlib import Path

def run(cmd): subprocess.run(cmd,check=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--clips",required=True,help="JSON array of clip paths in story order")
    p.add_argument("--output",default="documentary.mp4")
    p.add_argument("--subtitles",help="Optional synchronized Persian SRT")
    p.add_argument("--burn-subtitles",action="store_true")
    p.add_argument("--voiceover",help="Optional final narration audio file")
    a=p.parse_args()
    clips=json.loads(Path(a.clips).read_text(encoding="utf-8"))
    if not isinstance(clips,list) or not clips: raise SystemExit("clips must be a non-empty JSON array.")
    paths=[Path(x).resolve() for x in clips]
    for x in paths:
      if not x.is_file(): raise SystemExit(f"Clip not found: {x}")
    out=Path(a.output).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
      normalized=[]
      for i,src in enumerate(paths):
        target=Path(tmp)/f"clip_{i:05d}.mp4"
        run(["ffmpeg","-y","-i",str(src),"-map","0:v:0","-map","0:a:0?","-vf","scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30","-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac","-ar","48000","-ac","2","-af","aresample=async=1","-pix_fmt","yuv420p","-movflags","+faststart",str(target)])
        normalized.append(target)
      manifest=Path(tmp)/"concat.txt"
      manifest.write_text("".join("file '"+str(x).replace("'","'\\''")+"'\n" for x in normalized),encoding="utf-8")
      joined=Path(tmp)/"joined.mp4"
      run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(manifest),"-c","copy",str(joined)])
      current=joined
      if a.voiceover:
        voice=Path(a.voiceover).resolve()
        if not voice.is_file(): raise SystemExit("Voiceover file not found.")
        voiced=Path(tmp)/"voiced.mp4"
        run(["ffmpeg","-y","-i",str(joined),"-i",str(voice),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-shortest",str(voiced)])
        current=voiced
      if a.subtitles and a.burn_subtitles:
        srt=Path(a.subtitles).resolve()
        if not srt.is_file(): raise SystemExit("Subtitle file not found.")
        # Soft-burn uses FFmpeg subtitles filter; input SRT is UTF-8.
        run(["ffmpeg","-y","-i",str(current),"-vf",f"subtitles={str(srt).replace(':','\\:')}:force_style='FontName=DejaVu Sans,FontSize=22,Outline=2,Shadow=1,Alignment=2,MarginV=36'","-c:v","libx264","-preset","veryfast","-crf","20","-c:a","copy","-movflags","+faststart",str(out)])
      else:
        run(["ffmpeg","-y","-i",str(current),"-c","copy",str(out)])
    print(f"DOCUMENTARY_ASSEMBLED {out}")
    print("Review clip continuity, audio loudness, subtitle timing, rights, and factual accuracy before publishing.")
if __name__=="__main__": main()
