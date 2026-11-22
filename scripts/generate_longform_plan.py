#!/usr/bin/env python3
"""Draft an English documentary script from approved evidence using free LLM routes."""
import argparse, json, os, re, sys, time, urllib.request
from pathlib import Path
from urllib.parse import urlparse
from free_model_router import discover_free_models
from avalai_client import AvalAIClient


def confirmed_claims(dossier):
    sources = {str(s.get("id")): s for s in dossier.get("sources", []) if isinstance(s, dict) and s.get("id")}
    result = []
    for claim in dossier.get("claims", []):
        if not isinstance(claim, dict) or claim.get("status") != "confirmed":
            continue
        ids = [str(x) for x in claim.get("source_ids", []) if str(x) in sources]
        hosts = {urlparse(str(sources[x].get("url", ""))).hostname for x in ids
                 if urlparse(str(sources[x].get("url", ""))).scheme == "https"}
        if len(hosts) >= 2 and claim.get("id") and claim.get("claim"):
            result.append({"id": str(claim["id"]), "claim": str(claim["claim"]), "source_ids": ids})
    return result


def build_prompt(dossier, target_seconds):
    claims = confirmed_claims(dossier)
    if len(claims) < 3:
        raise ValueError("At least three independently sourced confirmed claims are required.")
    minimum = max(600, target_seconds * 2)
    return (
        "Write a compelling, factual English documentary script and visual storyboard. "
        f"Topic: {dossier.get('topic', '')}. Runtime: {target_seconds} seconds. "
        f"Write at least {minimum} narration words at a natural documentary pace. "
        "Use ONLY the confirmed claims below. Never invent dates, names, numbers, quotations, "
        "causes, or explanations. Each chapter must cite exact claim_ids. Do not use disputed "
        "or unverified material. Create 5-30 chapters; each narration must contain 100-260 words. "
        "Each chapter needs 2-5 scene briefs with visual_query (at least 3 words), media_type "
        "(image or video), duration_seconds (4-30), and purpose. The sum of all scene durations "
        "MUST cover the full target runtime; aim for 20-30 seconds per scene and add enough scenes. "
        "Prefer public-domain archival, "
        "educational, landscape, map, and neutral illustrative visuals. Do not request movie/TV "
        "clips, broadcast footage, logos, or celebrity likenesses. Return only JSON with keys "
        "title, logline, chapters. CONFIRMED CLAIMS:\n"
        + json.dumps(claims, ensure_ascii=False, indent=2)
    )


def validate_plan(plan, dossier, target_seconds):
    allowed = {c["id"] for c in confirmed_claims(dossier)}
    chapters = plan.get("chapters")
    if not isinstance(chapters, list) or not 5 <= len(chapters) <= 30:
        raise ValueError("Plan must contain 5-30 chapters.")
    output, seen, words, visual_seconds = [], set(), 0, 0
    for index, row in enumerate(chapters, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Chapter {index} must be an object.")
        cid = str(row.get("id", f"CH{index}")).strip()
        title = str(row.get("title", "")).strip()
        narration = re.sub(r"\s+", " ", str(row.get("narration", ""))).strip()
        count = len(narration.split())
        claim_ids = list(dict.fromkeys(str(x) for x in row.get("claim_ids", [])))
        if not cid or cid in seen or not title or not 100 <= count <= 260:
            raise ValueError(f"Chapter {index} has an invalid ID, title, or narration length ({count}).")
        if not claim_ids or set(claim_ids) - allowed:
            raise ValueError(f"Chapter {index} has missing or unapproved claim IDs.")
        scenes = row.get("scenes")
        if not isinstance(scenes, list) or not 2 <= len(scenes) <= 5:
            raise ValueError(f"Chapter {index} needs 2-5 scenes.")
        clean = []
        for scene in scenes:
            if not isinstance(scene, dict):
                raise ValueError("Scene must be an object.")
            query = re.sub(r"\s+", " ", str(scene.get("visual_query", ""))).strip()
            kind = scene.get("media_type", "image")
            duration = float(scene.get("duration_seconds", 8))
            if len(query.split()) < 3 or kind not in ("image", "video") or not 4 <= duration <= 30:
                raise ValueError("Scene has invalid query, type, or duration.")
            clean.append({"visual_query": query, "media_type": kind,
                          "duration_seconds": duration, "purpose": str(scene.get("purpose", ""))[:200]})
            visual_seconds += duration
        seen.add(cid)
        words += count
        output.append({"id": cid, "title": title[:160], "narration": narration,
                       "word_count": count, "claim_ids": claim_ids, "scenes": clean})
    minimum = max(600, target_seconds * 2)
    if words < minimum:
        raise ValueError(f"Only {words} narration words; at least {minimum} are required.")
    if visual_seconds < target_seconds * 1.2:
        raise ValueError(f"Planned visuals cover only {visual_seconds:.1f}s; at least {target_seconds * 1.2:.1f}s are required for narration timing headroom.")
    if not str(plan.get("title", "")).strip() or not str(plan.get("logline", "")).strip():
        raise ValueError("Plan requires title and logline.")
    return {
        "schema_version": 1, "topic": dossier.get("topic", ""),
        "title": str(plan["title"])[:160], "logline": str(plan["logline"])[:500],
        "target_duration_seconds": target_seconds, "narration_word_count": words, "planned_visual_seconds": round(visual_seconds, 2),
        "chapters": output, "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "editorial_status": "AI_DRAFT_REQUIRES_SOURCE_AND_EDITORIAL_REVIEW",
        "warning": "Claim IDs do not prove every sentence. Verify narration against source passages before publication."
    }


def request_json(base, key, model, prompt):
    payload = {"model": model, "messages": [
        {"role": "system", "content": "Write accurate documentary narration. Return only JSON. Never invent facts."},
        {"role": "user", "content": prompt}],
        "temperature": 0.2, "max_tokens": 12000, "response_format": {"type": "json_object"}}
    if base.rstrip("/") in ("https://api.avalai.ir/v1", "https://api.avalapis.ir/v1", "https://api.avalai.org/v1"):
        content = AvalAIClient(api_key=key, base_url=base).chat_completion(
            model, payload["messages"], temperature=0.2, max_tokens=12000,
            response_format={"type": "json_object"})
        data = {"choices": [{"message": {"content": content}}]}
    else:
        req = urllib.request.Request(base.rstrip("/") + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=240) as response:
            data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Model returned no choices.")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "\n".join(x.get("text", "") for x in content if isinstance(x, dict))
    fence = chr(96) * 3
    content = str(content).strip()
    if content.startswith(fence):
        content = content[len(fence):]
        if content.lower().startswith("json"):
            content = content[4:]
        if content.rstrip().endswith(fence):
            content = content.rstrip()[:-len(fence)]
    first, last = content.find("{"), content.rfind("}")
    if first < 0 or last <= first:
        raise ValueError("Model response is not JSON.")
    return json.loads(content[first:last + 1])


def routes():
    result = []
    base, key = os.getenv("FREELLMAPI_BASE_URL", "").strip(), os.getenv("FREELLMAPI_API_KEY", "").strip()
    if base and key:
        try:
            result += [("FreeLLMAPI", base, key, m) for m in discover_free_models(
                base, key, task="general", preferred=os.getenv("FREELLMAPI_MODEL", "auto"))]
        except Exception as exc:
            print("FREELLMAPI discovery failed:", type(exc).__name__, file=sys.stderr)
    avalai_key = os.getenv("AVALAI_API_KEY", "").strip()
    if avalai_key:
        base = os.getenv("AVALAI_BASE_URL", "https://api.avalai.ir/v1").strip()
        try:
            result += [("AvalAI", base, avalai_key, m) for m in discover_free_models(
                base, avalai_key, task="general", preferred=os.getenv("AVALAI_MODEL", "auto"))]
        except Exception as exc:
            print("AvalAI discovery failed:", type(exc).__name__, file=sys.stderr)
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if key:
        base = "https://openrouter.ai/api/v1"
        try:
            result += [("OpenRouter", base, key, m) for m in discover_free_models(
                base, key, task="general", preferred=os.getenv("OPENROUTER_MODEL", "auto"))]
        except Exception as exc:
            print("OpenRouter discovery failed:", type(exc).__name__, file=sys.stderr)
    return result


def generate(research, output, target_seconds):
    dossier = json.loads(Path(research).read_text(encoding="utf-8"))
    prompt = build_prompt(dossier, target_seconds)
    candidates = routes()
    if not candidates:
        raise RuntimeError("No explicitly free LLM model discovered; unknown-price models are excluded.")
    errors = []
    for provider, base, key, model in candidates:
        try:
            result = validate_plan(request_json(base, key, model, prompt), dossier, target_seconds)
            result["provider"], result["model"] = provider, model
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return result
        except Exception as exc:
            errors.append(f"{provider}/{model}: {type(exc).__name__}: {str(exc)[:180]}")
            print(f"MODEL_ATTEMPT_FAILED provider={provider} model={model} error={type(exc).__name__}", file=sys.stderr)
    raise RuntimeError("All free model routes failed: " + " | ".join(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", required=True)
    parser.add_argument("--output", default="longform-output/longform-plan.json")
    parser.add_argument("--target-duration-seconds", type=int, default=480)
    args = parser.parse_args()
    if not 300 <= args.target_duration_seconds <= 3600:
        raise SystemExit("Target runtime must be 300-3600 seconds.")
    try:
        result = generate(args.research, args.output, args.target_duration_seconds)
    except Exception as exc:
        raise SystemExit(f"LONGFORM_PLAN_FAILED: {exc}") from exc
    print(f"LONGFORM_PLAN_READY chapters={len(result['chapters'])} words={result['narration_word_count']} provider={result['provider']} model={result['model']}")


if __name__ == "__main__":
    main()
