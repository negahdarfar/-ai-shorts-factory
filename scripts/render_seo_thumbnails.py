#!/usr/bin/env python3
"""Render clean 1280x720 thumbnail drafts from the SEO manifest using Pillow."""
import argparse, json, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def font(size, bold=True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
    ]
    for item in candidates:
        if Path(item).exists(): return ImageFont.truetype(item, size)
    return ImageFont.load_default()

def wrap(draw, text, fnt, max_width, max_lines=3):
    words, lines, line = re.sub(r"\s+", " ", str(text)).split(), [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0,0), candidate, font=fnt)[2] <= max_width: line = candidate
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines[:max_lines]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="seo_metadata.json"); p.add_argument("--output-dir",default="seo_thumbnails")
    a=p.parse_args(); records=json.loads(Path(a.input).read_text(encoding="utf-8"))
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    for i,row in enumerate(records,1):
        meta=row["metadata"]; title=meta.get("title") or row.get("topic","")
        concept=meta.get("thumbnail_concept","")
        img=Image.new("RGB",(1280,720),(18,25,42))
        # Subtle diagonal panels and a dark text-safe area; no generated factual imagery.
        overlay=Image.new("RGBA",img.size,(0,0,0,0)); d=ImageDraw.Draw(overlay)
        d.polygon([(780,0),(1280,0),(1280,720),(500,720)],fill=(35,92,125,180))
        d.ellipse((850,-220,1450,380),fill=(255,190,75,110))
        overlay=overlay.filter(ImageFilter.GaussianBlur(2)); img=Image.alpha_composite(img.convert("RGBA"),overlay)
        draw=ImageDraw.Draw(img)
        draw.rounded_rectangle((52,52,1228,668),radius=32,outline=(255,255,255,70),width=3)
        draw.text((90,100),"THE SHORTS FACTORY",font=font(25),fill=(255,202,110,255))
        lines=wrap(draw,title.upper(),font(70),1050,3)
        y=210
        for line in lines:
            draw.text((90,y),line,font=font(70),fill=(255,255,255,255),stroke_width=2,stroke_fill=(0,0,0,100)); y+=92
        if concept:
            short=concept[:115]
            draw.text((92,570),short,font=font(23,False),fill=(220,230,240,255))
        name=f"{i:02d}-{re.sub(r'[^a-z0-9]+','-',row.get('topic','topic').lower()).strip('-')[:45]}.jpg"
        img.convert("RGB").save(out/name,"JPEG",quality=92,optimize=True)
        print(f"THUMBNAIL_DRAFT_CREATED {out/name}")
if __name__=="__main__": main()
