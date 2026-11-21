#!/usr/bin/env python3
"""Generate SEO, narration scripts and footage terms through free LLM gateways, with safe local fallback."""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from free_model_router import discover_free_models

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
SEO_FIELDS = ("primary_keyword", "secondary_keywords", "title", "description", "hashtags", "tags", "pinned_comment", "thumbnail_concept", "search_intent")


def clean(value, limit=None):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    return value[:limit] if limit else value


def extract_json(raw):
    raw = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw.strip(), flags=re.I)
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
    """Topic-specific conservative metadata used only as a draft if the AI quota is unavailable."""
    keyword = clean(topic, 80)
    display = keyword.title()
    title = f"{display}: The Story Behind the Topic"[:100]
    tags = list(dict.fromkeys([keyword.lower(), *[w.lower() for w in re.findall(r"[A-Za-z0-9]+", keyword) if len(w) > 2], "short documentary", "explained"]))[:15]
    return {
        "primary_keyword": keyword,
        "secondary_keywords": [f"{display} explained", f"{display} facts", f"{display} background"],
        "title": title,
        "description": f"Explore {keyword} in this short documentary. This video introduces the subject, explains its context, and highlights the key questions viewers should understand.",
        "hashtags": ["Shorts", "Documentary", "Explained"],
        "tags": tags,
        "pinned_comment": f"What question about {keyword} should we explore next?",
        "thumbnail_concept": f"A clear, authentic visual directly connected to {keyword}; use no unlicensed logos, celebrity images, or copyrighted footage.",
        "search_intent": f"Learn the background and context of {keyword}."
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
    if word_count < 155 or word_count > 270:
        raise ValueError(f"video_script must contain 155-270 words for a 60-120 second Short, got {word_count}")
    if len(terms) < 5:
        raise ValueError("At least five stock-footage search terms are required")
    return {"metadata": metadata, "video_script": script, "video_terms": terms}


def generate_batch(topics, language, model, key, research=None, api_base_url=None, api_key=None, api_model="auto", api_provider="FreeLLMAPI", max_attempts=3, repair_missing=True):
    topic_text = "\\n".join(f"{i}. {topic}" for i, topic in enumerate(topics, 1))
    research_by_topic = {}
    for row in (research or {}).get("topics", []):
        research_by_topic[clean(row.get("query", "")).casefold()] = row
    viral_context = []
    for topic in topics:
        sample = research_by_topic.get(topic.casefold(), {})
        viral_context.append({
            "topic": topic,
            "sample_size": sample.get("videos_found", 0),
            "breakout_signal": sample.get("top_breakout_signal"),
            "hook_pattern_counts": sample.get("title_hook_pattern_counts", {}),
            "top_examples": [
                {
                    "title": x.get("title"),
                    "views_per_day_estimate": x.get("views_per_day_estimate"),
                    "likes_per_view": x.get("likes_per_view"),
                    "comments_per_view": x.get("comments_per_view"),
                }
                for x in sample.get("top_competitors", [])[:5]
            ],
        })
    viral_context_text = json.dumps(viral_context, ensure_ascii=False)
    prompt = f"""You are the research-aware writer and YouTube SEO editor for a factual short documentary channel.
Create ALL deliverables for every topic below in ONE response. Output language: {language}.
Topics:
{topic_text}

Public YouTube Shorts breakout research (directional sample; not guaranteed viral):
{viral_context_text}

Use the research to identify audience-interest patterns, opening-hook structures, pacing and subject angles that appear in stronger recent Shorts. Do NOT copy competitor titles, scripts, exact phrasing, footage, thumbnails, or distinctive creative expression. Invent a genuinely original angle and narrative for each topic. Prioritize a compelling first 1-2 seconds, fast context, escalating curiosity, concrete visual beats, a satisfying factual payoff, and a natural ending. Do not fabricate performance claims or treat views/day as a guaranteed viral predictor. If research is absent for a topic, say nothing about competitor performance and use editorial judgment.

Return ONLY valid JSON in this structure:
{{"items":[{{"index":1,"video_script":"155-270 spoken words, no title or markdown","video_terms":["8 concrete stock-footage search phrases"],"metadata":{{"primary_keyword":"natural search phrase","secondary_keywords":["3-6 relevant phrases"],"title":"accurate compelling title under 100 characters","description":"2-4 useful sentences","hashtags":["up to 3, no #"],"tags":["8-15 relevant tags"],"pinned_comment":"useful question","thumbnail_concept":"specific visual idea","search_intent":"viewer intent"}}}}]}}
Exactly one indexed item per input topic. Each script MUST contain 155-270 spoken words (never fewer than 155 or more than 270). Count the words before returning each item; aim for 210-230 words. Script must have a strong opening, clear explanation and natural payoff. Use short concrete narration sentences that can be illustrated by relevant real footage. Do not invent statistics, dates, quotes, legal holdings, scientific claims or other facts. If the topic is disputed or current, clearly distinguish established facts from allegations or opinions; if facts are uncertain, say so or omit them. Search terms must be concrete, topic-specific visual phrases in English, 2-4 words each, not generic filler. Across all four topics, each item's visual search phrases must be distinct and must not reuse the same generic b-roll concepts. Select visuals that could not plausibly be swapped between topics. Every title must be unique and explicitly name the real topic or named entity; avoid generic titles such as 'Interesting Facts' or 'Explained'. The primary keyword must closely match the input topic and appear naturally in the title. Write a useful description with specific verified context, a concise opening hook, and a natural viewer question. SEO must be accurate, natural and not keyword-stuffed. Never claim keyword volume, CTR or ranking data."""
    if api_base_url and api_key:
        payload = {
            "model": api_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a research-aware factual documentary writer and YouTube SEO editor. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.25,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
        }
        request_url = api_base_url.rstrip("/") + "/chat/completions"
        request_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        provider = api_provider
    else:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        request_url = f"{API_ROOT}/{model}:generateContent?key={key}"
        request_headers = {"Content-Type": "application/json"}
        provider = "Gemini"

    result = {}
    for attempt in range(max(1, max_attempts)):
        req = urllib.request.Request(
            request_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=request_headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=180 if provider in ("FreeLLMAPI", "Cloudflare", "OpenRouter") else 150) as response:
                data = json.loads(response.read().decode("utf-8"))
            if provider in ("FreeLLMAPI", "Cloudflare", "OpenRouter"):
                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("FreeLLMAPI returned no chat completion choices.")
                raw = choices[0].get("message", {}).get("content", "")
                if isinstance(raw, list):
                    raw = "\\n".join(part.get("text", "") for part in raw if isinstance(part, dict))
                raw = str(raw)
            else:
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                raw = "\\n".join(p.get("text", "") for p in parts)
            parsed = extract_json(raw)
            for row in parsed.get("items", []):
                try:
                    index = int(row["index"])
                    if 1 <= index <= len(topics):
                        result[index] = normalize_item(row, topics[index - 1])
                except (KeyError, TypeError, ValueError) as exc:
                    print(f"Discarding incomplete {provider} item: {exc}", file=sys.stderr)
            expected = set(range(1, len(topics) + 1))
            missing = sorted(expected - set(result))
            if missing:
                if attempt < max(1, max_attempts) - 1:
                    delay = 2 ** (attempt + 1)
                    print(
                        f"{provider.upper()}_INCOMPLETE_BATCH; retrying full batch in {delay}s "
                        f"(attempt {attempt + 2}/3).",
                        file=sys.stderr,
                        flush=True,
                    )
                    time.sleep(delay)
                    continue
                if repair_missing:
                    # Repair only missing items with one focused request each.
                    # Valid batch items are preserved rather than discarded.
                    for missing_index in missing:
                        try:
                            repaired = generate_batch(
                                [topics[missing_index - 1]], language, model, key,
                                research=research, api_base_url=api_base_url,
                                api_key=api_key, api_model=api_model,
                                api_provider=api_provider, max_attempts=1,
                                repair_missing=False,
                            )
                            if 1 in repaired:
                                result[missing_index] = repaired[1]
                        except (RuntimeError, ValueError, OSError) as repair_error:
                            print(
                                f"{provider.upper()}_SINGLE_ITEM_REPAIR_FAILED "
                                f"| item={missing_index} | {repair_error}",
                                file=sys.stderr, flush=True,
                            )
                    missing = sorted(set(range(1, len(topics) + 1)) - set(result))
                if missing:
                    raise RuntimeError(
                        f"{provider} returned an incomplete content batch after retries and "
                        f"single-item repair; missing item(s): {missing}. "
                        "Trying the next explicitly permitted provider."
                    )
            return result
        except (ValueError, KeyError, TypeError) as exc:
            if attempt == 2:
                raise RuntimeError(f"{provider} returned invalid content after three attempts: {exc}") from exc
            delay = 2 ** (attempt + 1)
            print(
                f"{provider.upper()}_INVALID_CONTENT; retrying in {delay}s (attempt {attempt + 2}/3).",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            message = f"{provider} HTTP {exc.code}: {detail}"
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(message) from exc
            if exc.code == 429 and any(marker in message.lower() for marker in (
                "generate_content_free_tier_requests", "per_day", "daily limit", "free_tier_requests"
            )):
                raise RuntimeError(message) from exc
            time.sleep(2 ** (attempt + 1))
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt == 2:
                raise RuntimeError(f"{provider} connection error: {exc}") from exc
            time.sleep(2 ** (attempt + 1))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="trending_batch.json")
    parser.add_argument("--output", default="seo_metadata.json")
    parser.add_argument("--language", default="English")
    parser.add_argument("--model", default=os.getenv("SEO_GEMINI_MODEL", "gemini-3.8-flash"))
    parser.add_argument("--research", default="youtube_competitor_research.json")
    parser.add_argument("--require-viral-research", action="store_true")
    parser.add_argument("--require-ai-batch", action="store_true")
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    research = None
    research_path = Path(args.research)
    if research_path.is_file():
        research = json.loads(research_path.read_text(encoding="utf-8"))
    if args.require_viral_research and not research:
        raise SystemExit("Public YouTube viral-pattern research is required but unavailable.")
    if args.require_viral_research:
        found = {clean(row.get("query", "")).casefold() for row in research.get("topics", [])}
        missing = [clean(row.get("video_subject", "")).casefold() for row in source if clean(row.get("video_subject", "")).casefold() not in found]
        if missing:
            raise SystemExit("Missing public competitor research for one or more selected topics.")
    if not isinstance(source, list) or not source:
        raise SystemExit("Input must be a non-empty list")
    topics = [clean(row.get("video_subject") if isinstance(row, dict) else "") for row in source]
    if any(not topic for topic in topics):
        raise SystemExit("Every input item must have video_subject")

    generated = {}
    generated_source = "local_template_fallback"
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_free_tier_enabled = os.getenv("GEMINI_FREE_TIER_ENABLED", "false").strip().lower() == "true"
    allow_nonfree_fallback = os.getenv("ALLOW_NONFREE_LLM_FALLBACK", "false").strip().lower() == "true"
    cloudflare_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    cloudflare_api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    cloudflare_model = os.getenv("CLOUDFLARE_MODEL", "@cf/zai-org/glm-4.7-flash").strip()
    gateways = []
    if cloudflare_account_id and cloudflare_api_token and cloudflare_model == "@cf/zai-org/glm-4.7-flash":
        gateways.append((
            "Cloudflare",
            f"https://api.cloudflare.com/client/v4/accounts/{cloudflare_account_id}/ai/v1",
            cloudflare_api_token,
            cloudflare_model,
        ))
    elif cloudflare_account_id or cloudflare_api_token:
        print("CLOUDFLARE_CONFIGURATION_INCOMPLETE_OR_MODEL_NOT_ALLOWLISTED; refusing unknown-price routing.", file=sys.stderr)
    # Optional always-on hosted FreeLLMAPI endpoint (not the phone/Tailscale gateway).
    freellmapi_cloud_url = os.getenv("FREELLMAPI_CLOUD_BASE_URL", "").strip()
    if freellmapi_cloud_url:
        gateways.append((
            "FreeLLMAPI",
            freellmapi_cloud_url,
            os.getenv("FREELLMAPI_API_KEY", "").strip(),
            os.getenv("FREELLMAPI_MODEL", "auto").strip() or "auto",
        ))
    else:
        gateways.append((
            "FreeLLMAPI",
            os.getenv("FREELLMAPI_BASE_URL", "").strip(),
            os.getenv("FREELLMAPI_API_KEY", "").strip(),
            os.getenv("FREELLMAPI_MODEL", "auto").strip() or "auto",
        ))
    # OpenRouter exposes rotating explicitly-free models through one OpenAI-compatible API.
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        gateways.append((
            "OpenRouter",
            "https://openrouter.ai/api/v1",
            openrouter_key,
            os.getenv("OPENROUTER_MODEL", "auto").strip() or "auto",
        ))
    if allow_nonfree_fallback:
        gateways.append((
            "OmniRoute",
            os.getenv("OMNIROUTE_BASE_URL", "").strip(),
            os.getenv("OMNIROUTE_API_KEY", "").strip(),
            os.getenv("OMNIROUTE_MODEL", "auto").strip() or "auto",
        ))
    elif os.getenv("OMNIROUTE_API_KEY", "").strip():
        print("NON_FREE_LLM_FALLBACK_DISABLED; OmniRoute will not be called.", flush=True)
    # Run each topic as its own request: free models often truncate four-item batches.
    provider_routes = []
    for provider, base_url, api_key, api_model in gateways:
        if not (base_url and api_key):
            continue
        if provider in ("FreeLLMAPI", "OpenRouter"):
            try:
                candidate_models = discover_free_models(base_url, api_key, task="seo", preferred=api_model)
            except Exception as discovery_error:
                candidate_models = []
                print(f"{provider.upper()}_MODEL_DISCOVERY_FAILED: {discovery_error}", file=sys.stderr)
            if not candidate_models:
                print(f"{provider.upper()}_NO_EXPLICITLY_FREE_MODELS; skipping unknown-price routing.", file=sys.stderr)
                continue
        else:
            candidate_models = [api_model]
        for selected_model in candidate_models:
            provider_routes.append((provider, base_url, api_key, selected_model))

    # Prefer the private FreeLLMAPI gateway when configured; Cloudflare remains the
    # unattended fallback if the phone/Tailscale gateway cannot be reached.
    provider_routes.sort(key=lambda route: 0 if route[0] == "FreeLLMAPI" else 1)
    gemini_free_model = os.getenv("SEO_GEMINI_MODEL", args.model).strip()
    for topic_index, topic in enumerate(topics, 1):
        topic_succeeded = False
        for provider, base_url, api_key, selected_model in provider_routes:
            try:
                one = generate_batch([topic], args.language, args.model, "", research=research,
                    api_base_url=base_url, api_key=api_key, api_model=selected_model,
                    api_provider=provider, max_attempts=2, repair_missing=False)
                if 1 not in one:
                    raise RuntimeError("Provider returned no validated item.")
                generated[topic_index] = one[1]
                print(f"SEO_ITEM_GENERATED | item={topic_index}/{len(topics)} | provider={provider} | model={selected_model}", flush=True)
                topic_succeeded = True
                break
            except (RuntimeError, ValueError, OSError) as gateway_error:
                print(f"{provider.upper()}_ITEM_FAILED_NEXT_ROUTE | item={topic_index} | model={selected_model} | {gateway_error}", file=sys.stderr, flush=True)
        if not topic_succeeded and gemini_key and gemini_free_tier_enabled:
            try:
                one = generate_batch([topic], args.language, gemini_free_model, gemini_key, research=research, max_attempts=2, repair_missing=False)
                if 1 not in one:
                    raise RuntimeError("Gemini returned no validated item.")
                generated[topic_index] = one[1]
                print(f"SEO_ITEM_GENERATED | item={topic_index}/{len(topics)} | provider=Gemini_Free_Tier | model={gemini_free_model}", flush=True)
                topic_succeeded = True
            except (RuntimeError, ValueError, OSError) as gemini_error:
                print(f"GEMINI_FREE_TIER_ITEM_FAILED | item={topic_index} | {gemini_error}", file=sys.stderr, flush=True)
        if not topic_succeeded:
            print(f"SEO_ITEM_UNAVAILABLE | item={topic_index}/{len(topics)} | no approved free provider produced a valid item.", file=sys.stderr, flush=True)
    if gemini_key and not gemini_free_tier_enabled:
        print("GEMINI_FALLBACK_SKIPPED: enable only after confirming Google AI Studio Free Tier.", file=sys.stderr)
    generated_source = "multi_provider_individual"
    gateway_succeeded = len(generated) == len(topics)

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
            "metadata_source": generated_source if is_ai else "local_template_fallback",
            "content_source": generated_source if is_ai else "local_template_fallback",
            "requires_final_script_review": True
        })

    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    ai_count = sum(row["content_source"] != "local_template_fallback" for row in output)
    print(f"CONTENT_BATCH_READY: {len(output)} records; AI={ai_count}; local_fallback={len(output)-ai_count}")
    if ai_count < len(output):
        message = (
            f"AI content batch incomplete: {ai_count}/{len(output)} items came from an approved provider. "
            "Local fallback drafts are not publishable."
        )
        print("CONTENT_REVIEW_WARNING: " + message, file=sys.stderr)
        if args.require_ai_batch:
            raise SystemExit(message)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"Content generation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
