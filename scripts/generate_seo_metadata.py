#!/usr/bin/env python3
"""Generate SEO, narration scripts and footage terms in one Gemini batch, with safe local fallback."""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
SEO_FIELDS = ("primary_keyword", "secondary_keywords", "title", "description", "hashtags", "tags", "pinned_comment", "thumbnail_concept", "search_intent")


def clean(value, limit=None):
    value = re.sub(r"\\s+", " ", str(value or "")).strip()
    return value[:limit] if limit else value


def extract_json(raw):
    raw = re.sub(r"^\\s*```(?:json)?\\s*|\\s*```\\s*$", "", raw.strip(), flags=re.I)
    left, right = raw.find("{"), raw.rfind("}")
    if left < 0 or right <= left:
        raise ValueError("No JSON object in Gemini response")
    return json.loads(raw[left:right + 1])


def fallback_content(topic):
    """Conservative narration and search terms; no topic-specific facts are invented."""
    topic = clean(topic, 160)
    script = (
        f"Let's take a closer look at {topic}. The first question is simple: what does this subject "
        "actually mean, and what evidence helps us understand it? Start with the central idea, "
        "then look at the people, places, objects, or processes connected to it. Context matters, "
        "because a short headline can leave out details that change the meaning. A useful way to "
        f"explore {topic} is to separate confirmed information from assumptions and ask what the "
        "available evidence really shows. That gives us a clearer picture without overstating what "
        "is known. So when you come across this subject, look beyond the headline, check the context, "
        "and follow the evidence. That's how to understand the story more carefully."
    )
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", topic) if len(w) > 2]
    lead = words[0] if words else "topic"
    terms = list(dict.fromkeys([
        topic[:70], " ".join(words[:3]), " ".join(words[-3:]),
        *words, f"{lead} background", f"{lead} explained",
        "documentary footage", "real world example"
    ]))
    terms = [clean(x, 80) for x in terms if clean(x)]
    return script, terms[:8]


def fallback_metadata(topic):
    keyword = clean(re.sub(r"[^\\w\\s'-]", " ", topic), 80) or "interesting facts"
    title = (keyword + ": Explained")[:100]
    return {
        "primary_keyword": keyword,
        "secondary_keywords": ["explained", "how it works", "quick facts"],
        "title": title,
        "description": f"Discover {keyword.lower()} in this concise educational explainer. Learn the key idea, context, and what evidence helps explain it.",
        "hashtags": ["Shorts", "Explained", "Education"],
        "tags": list(dict.fromkeys([keyword.lower(), "explained", "educational video"] + [w.lower() for w in keyword.split() if len(w) > 2]))[:15],
        "pinned_comment": f"What would you like to know next about {keyword.lower()}?",
        "thumbnail_concept": f"A clear, topic-specific visual showing {keyword.lower()}, with minimal text.",
        "search_intent": f"Understand {keyword.lower()} quickly."
    }


def normalize_item(item, topic):
    if not isinstance(item, dict):
        raise ValueError("Batch item must be an object")
    meta = item.get("metadata")
    if not isinstance(meta, dict) or any(k not in meta for k in SEO_FIELDS):
        raise ValueError("Incomplete SEO metadata object")
    metadata = {
        "primary_keyword": clean(meta["primary_keyword"], 100),
        "secondary_keywords": [clean(x, 100) for x in (meta["secondary_keywords"] or [])[:6]],
        "title": clean(meta["title"], 100),
        "description": clean(meta["description"], 5000),
        "hashtags": [clean(x, 60).lstrip("#") for x in (meta["hashtags"] or [])[:3]],
        "tags": list(dict.fromkeys(clean(x, 60) for x in (meta["tags"] or [])[:15] if clean(x))),
        "pinned_comment": clean(meta["pinned_comment"], 500),
        "thumbnail_concept": clean(meta["thumbnail_concept"], 400),
        "search_intent": clean(meta["search_intent"], 300)
    }
    if not metadata["primary_keyword"] or not metadata["title"] or not metadata["description"]:
        raise ValueError("Empty required SEO field")
    # Keep the model's selected primary keyword visibly aligned with the metadata.
    # Add it naturally to the description when the generated title/description omit it.
    primary = metadata["primary_keyword"]
    if primary.casefold() not in (metadata["title"] + " " + metadata["description"]).casefold():
        suffix = f" Explore {primary} in this concise video."
        metadata["description"] = (metadata["description"].rstrip() + suffix)[:5000]
    script = clean(item.get("video_script"), 8000)
    terms = item.get("video_terms")
    if not isinstance(terms, list):
        raise ValueError("video_terms must be a list")
    terms = list(dict.fromkeys(clean(x, 80) for x in terms if clean(x)))[:8]
    word_count = len(script.split())
    if word_count < 55 or word_count > 160:
        raise ValueError(f"video_script must contain 55-160 words, got {word_count}")
    if len(terms) < 5:
        raise ValueError("At least five stock-footage search terms are required")
    return {"metadata": metadata, "video_script": script, "video_terms": terms}


def generate_batch(topics, language, model, key):
    topic_text = "\\n".join(f"{i}. {topic}" for i, topic in enumerate(topics, 1))
    prompt = f"""You are the research-aware writer and YouTube SEO editor for a factual short documentary channel.
Create ALL deliverables for every topic below in ONE response. Output language: {language}.
Topics:
{topic_text}

Return ONLY valid JSON in this structure:
{{"items":[{{"index":1,"video_script":"80-120 spoken words, no title or markdown","video_terms":["8 concrete stock-footage search phrases"],"metadata":{{"primary_keyword":"natural search phrase","secondary_keywords":["3-6 relevant phrases"],"title":"accurate compelling title under 100 characters","description":"2-4 useful sentences","hashtags":["up to 3, no #"],"tags":["8-15 relevant tags"],"pinned_comment":"useful question","thumbnail_concept":"specific visual idea","search_intent":"viewer intent"}}}}]}}
Exactly one indexed item per input topic. Script should be 55-130 words, have a strong opening, clear explanation and natural payoff. Use short concrete narration sentences that can be illustrated by relevant real footage. Do not invent statistics, dates, quotes, legal holdings, scientific claims or other facts. If the topic is disputed or current, clearly distinguish established facts from allegations or opinions; if facts are uncertain, say so or omit them. Search terms must be concrete, topic-specific visual phrases in English, 1-4 words each, not generic filler. SEO must be accurate, natural and not keyword-stuffed. Never claim keyword volume, CTR or ranking data."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    req = urllib.request.Request(
        f"{API_ROOT}/{model}:generateContent?key={key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=150) as response:
                data = json.loads(response.read().decode("utf-8"))
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            parsed = extract_json("\\n".join(p.get("text", "") for p in parts))
            result = {}
            for row in parsed.get("items", []):
                try:
                    index = int(row["index"])
                    if 1 <= index <= len(topics):
                        result[index] = normalize_item(row, topics[index - 1])
                except (KeyError, TypeError, ValueError) as exc:
                    print(f"Discarding incomplete Gemini item: {exc}", file=sys.stderr)
            return result
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            message = f"Gemini HTTP {exc.code}: {detail}"
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(message) from exc
            if exc.code == 429 and any(marker in message.lower() for marker in (
                "generate_content_free_tier_requests", "per_day", "daily limit", "free_tier_requests"
            )):
                raise RuntimeError(message) from exc
            time.sleep(2 ** (attempt + 1))
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt == 2:
                raise RuntimeError(str(exc)) from exc
            time.sleep(2 ** (attempt + 1))
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="trending_batch.json")
    parser.add_argument("--output", default="seo_metadata.json")
    parser.add_argument("--language", default="English")
    parser.add_argument("--model", default=os.getenv("SEO_GEMINI_MODEL", "gemini-3.8-flash"))
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(source, list) or not source:
        raise SystemExit("Input must be a non-empty list")
    topics = [clean(row.get("video_subject") if isinstance(row, dict) else "") for row in source]
    if any(not topic for topic in topics):
        raise SystemExit("Every input item must have video_subject")

    generated = {}
    try:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        generated = generate_batch(topics, args.language, args.model, api_key)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"CONTENT_BATCH_FALLBACK_ACTIVATED: {exc}", file=sys.stderr)

    output = []
    for index, topic in enumerate(topics, 1):
        is_ai = index in generated
        if is_ai:
            content = generated[index]
        else:
            script, terms = fallback_content(topic)
            content = {
                "metadata": fallback_metadata(topic),
                "video_script": script,
                "video_terms": terms
            }
        output.append({
            "index": index,
            "topic": topic,
            "language": args.language,
            **content,
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "basis": "topic_and_optional_public_competitor_sample",
            "metadata_source": "gemini_batch" if is_ai else "local_template_fallback",
            "content_source": "gemini_batch" if is_ai else "local_template_fallback",
            "requires_final_script_review": True
        })

    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    ai_count = sum(row["content_source"] == "gemini_batch" for row in output)
    print(f"CONTENT_BATCH_READY: {len(output)} records; Gemini={ai_count}; local_fallback={len(output)-ai_count}")
    if ai_count < len(output):
        print("CONTENT_REVIEW_WARNING: fallback scripts are generic, fact-safe drafts; review and improve before public use.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"Content generation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
