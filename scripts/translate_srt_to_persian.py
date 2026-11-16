#!/usr/bin/env python3
"""Translate SRT captions into Persian while preserving every index and timestamp."""
import argparse, json, os, re, sys, time, urllib.request
from pathlib import Path

API="https://generativelanguage.googleapis.com/v1beta/models"
BLOCK=re.compile(r"^\s*(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3})\s*\n([\s\S]*?)\s*$")
def parse_srt(text):
    blocks=re.split(r"\n\s*\n",text.strip())
    rows=[]
    for block in blocks:
        m=BLOCK.match(block.strip())
        if not m: raise ValueError("Malformed SRT block; expected index, timestamp line and caption.")
        rows.append({"index":int(m.group(1)),"time":m.group(2),"text":m.group(3).replace("\n"," ")})
    return rows
def translate_batch(rows,key,model):
    prompt=("Translate these English subtitle lines into natural, concise Persian (Farsi). "
      "Preserve meaning, names, numbers and tone. Do not add explanations. Return ONLY JSON "
      "with a single key 'translations' containing exactly one Persian string per input line. "
      "Do not merge or split captions. Input JSON:\n"+json.dumps([r["text"] for r in rows],ensure_ascii=False))
    payload={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.15,"responseMimeType":"application/json"}}
    req=urllib.request.Request(f"{API}/{model}:generateContent?key={key}",data=json.dumps(payload).encode(),
      headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=90) as resp: data=json.loads(resp.read().decode())
    text="\n".join(p.get("text","") for p in data.get("candidates",[{}])[0].get("content",{}).get("parts",[]))
    start,end=text.find("{"),text.rfind("}")
    result=json.loads(text[start:end+1])["translations"]
    if not isinstance(result,list) or len(result)!=len(rows) or any(not str(x).strip() for x in result):
        raise ValueError("Translation response count mismatch or empty caption.")
    return [str(x).strip() for x in result]
def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",default="subtitles.fa.srt")
    p.add_argument("--model",default=os.getenv("SEO_GEMINI_MODEL","gemini-2.5-flash")); p.add_argument("--batch-size",type=int,default=30); a=p.parse_args()
    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key: raise SystemExit("GEMINI_API_KEY is required.")
    rows=parse_srt(Path(a.input).read_text(encoding="utf-8-sig"))
    if not rows: raise SystemExit("No subtitle entries found.")
    translated=[]
    for start in range(0,len(rows),max(1,min(a.batch_size,50))):
      batch=rows[start:start+max(1,min(a.batch_size,50))]
      texts=translate_batch(batch,key,a.model)
      translated.extend({**row,"text":txt} for row,txt in zip(batch,texts))
      print(f"Translated {len(translated)}/{len(rows)} subtitle cues.")
      time.sleep(0.2)
    output="\n\n".join(f"{r['index']}\n{r['time']}\n{r['text']}" for r in translated)+"\n"
    Path(a.output).write_text(output,encoding="utf-8")
    print(f"PERSIAN_SRT_CREATED {a.output}; timing and cue count preserved.")
if __name__=="__main__":
  try: main()
  except Exception as e: print(f"SRT translation failed: {e}",file=sys.stderr); raise SystemExit(1)
