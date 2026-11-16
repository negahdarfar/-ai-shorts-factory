#!/usr/bin/env python3
"""Batch-create four SEO drafts with one Gemini request and a local fallback."""
import argparse, json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
FIELDS = ("primary_keyword","secondary_keywords","title","description","hashtags","tags","pinned_comment","thumbnail_concept","search_intent")

def clean(value, limit=None):
    value = re.sub(r"\\s+", " ", str(value or "")).strip()
    return value[:limit] if limit else value

def extract_json(raw):
    raw = re.sub(r"^\\s*```(?:json)?\\s*|\\s*```\\s*$", "", raw.strip(), flags=re.I)
    left, right = raw.find("{"), raw.rfind("}")
    if left < 0 or right <= left:
        raise ValueError("No JSON object in Gemini response")
    return json.loads(raw[left:right+1])

def fallback(topic):
    keyword = clean(re.sub(r"[^\\w\\s'-]", " ", topic), 80) or "interesting facts"
    title = (keyword + ": Explained")[:100]
    return {
        "primary_keyword": keyword,
        "secondary_keywords": ["explained", "how it works", "quick facts"],
        "title": title,
        "description": f"Discover {keyword.lower()} in this concise educational explainer. Learn the key idea, how it works, and why it matters.",
        "hashtags": ["Shorts", "Explained", "Education"],
        "tags": list(dict.fromkeys([keyword.lower(), "explained", "educational video"] + [w.lower() for w in keyword.split() if len(w)>2]))[:15],
        "pinned_comment": f"What would you like to know next about {keyword.lower()}?",
        "thumbnail_concept": f"A clear, topic-specific visual showing {keyword.lower()}, with minimal text.",
        "search_intent": f"Understand {keyword.lower()} quickly."
    }

def normalize(meta, topic):
    if not isinstance(meta, dict) or any(k not in meta for k in FIELDS):
        raise ValueError("Incomplete SEO metadata object")
    out = {
        "primary_keyword": clean(meta["primary_keyword"],100),
        "secondary_keywords": [clean(x,100) for x in (meta["secondary_keywords"] or [])[:6]],
        "title": clean(meta["title"],100),
        "description": clean(meta["description"],5000),
        "hashtags": [clean(x,60).lstrip("#") for x in (meta["hashtags"] or [])[:3]],
        "tags": list(dict.fromkeys(clean(x,60) for x in (meta["tags"] or [])[:15] if clean(x))),
        "pinned_comment": clean(meta["pinned_comment"],500),
        "thumbnail_concept": clean(meta["thumbnail_concept"],400),
        "search_intent": clean(meta["search_intent"],300)
    }
    if not out["primary_keyword"] or not out["title"] or not out["description"]:
        raise ValueError("Empty required SEO field")
    return out

def generate_batch(topics, language, model, key):
    topic_text = "\\n".join(f"{i}. {t}" for i,t in enumerate(topics,1))
    prompt = f"""Create SEO metadata for all topics in one response. Language: {language}.
Topics:\\n{topic_text}
Return ONLY JSON: {{"items":[{{"index":1,"metadata":{{"primary_keyword":"phrase","secondary_keywords":["phrases"],"title":"accurate title","description":"2-4 useful sentences","hashtags":["up to 3"],"tags":["8-15 tags"],"pinned_comment":"useful question","thumbnail_concept":"specific visual idea","search_intent":"viewer intent"}}}}]}}
Return one indexed item per topic. No fabricated facts, misleading clickbait, keyword stuffing, or ranking/volume claims. Review against final video."""
    payload = {"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"responseMimeType":"application/json"}}
    req = urllib.request.Request(f"{API_ROOT}/{model}:generateContent?key={key}", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                data=json.loads(response.read().decode())
            parts=data.get("candidates",[{}])[0].get("content",{}).get("parts",[])
            parsed=extract_json("\\n".join(p.get("text","") for p in parts))
            result={}
            for item in parsed.get("items",[]):
                try:
                    idx=int(item["index"])
                    if 1 <= idx <= len(topics):
                        result[idx]=normalize(item.get("metadata"),topics[idx-1])
                except (KeyError,TypeError,ValueError):
                    continue
            return result
        except urllib.error.HTTPError as exc:
            detail=exc.read().decode("utf-8",errors="replace")[:2000]
            msg=f"Gemini HTTP {exc.code}: {detail}"
            if exc.code not in (429,500,502,503,504) or attempt==2:
                raise RuntimeError(msg)
            if exc.code==429 and any(x in msg.lower() for x in ("generate_content_free_tier_requests","per_day","daily limit","free_tier_requests")):
                raise RuntimeError(msg)
            time.sleep(2**(attempt+1))
        except (TimeoutError,urllib.error.URLError) as exc:
            if attempt==2: raise RuntimeError(str(exc))
            time.sleep(2**(attempt+1))
    return {}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="trending_batch.json")
    p.add_argument("--output",default="seo_metadata.json")
    p.add_argument("--language",default="English")
    p.add_argument("--model",default=os.getenv("SEO_GEMINI_MODEL","gemini-3.8-flash"))
    a=p.parse_args()
    source=json.loads(Path(a.input).read_text(encoding="utf-8"))
    if not isinstance(source,list) or not source: raise SystemExit("Input must be a non-empty list")
    topics=[clean(x.get("video_subject") if isinstance(x,dict) else "") for x in source]
    if any(not x for x in topics): raise SystemExit("Every topic must have video_subject")
    generated={}
    try:
        key=os.getenv("GEMINI_API_KEY","").strip()
        if not key: raise RuntimeError("GEMINI_API_KEY is not configured")
        generated=generate_batch(topics,a.language,a.model,key)
    except (RuntimeError,ValueError,OSError) as exc:
        print(f"SEO_FALLBACK_ACTIVATED: {exc}",file=sys.stderr)
    output=[]
    for i,topic in enumerate(topics,1):
        is_ai=i in generated
        output.append({"index":i,"topic":topic,"language":a.language,"metadata":generated.get(i) or fallback(topic),
          "generated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
          "basis":"topic_and_optional_public_competitor_sample",
          "metadata_source":"gemini_batch" if is_ai else "local_template_fallback",
          "requires_final_script_review":True})
    Path(a.output).write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    ai=sum(x["metadata_source"]=="gemini_batch" for x in output)
    print(f"SEO_METADATA_READY: {len(output)} records; Gemini={ai}; local_fallback={len(output)-ai}")
    if ai<len(output): print("SEO_REVIEW_WARNING: fallback is a basic draft, not AI keyword research.")

if __name__=="__main__":
    try: main()
    except (OSError,ValueError,RuntimeError,KeyError) as exc:
        print(f"SEO generation failed: {exc}",file=sys.stderr); raise SystemExit(1)
