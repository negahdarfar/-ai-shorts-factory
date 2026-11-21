#!/usr/bin/env python3
"""Create a private MoneyPrinterTurbo config from GitHub Actions secrets."""
import os
from pathlib import Path
import toml
from free_model_router import discover_free_models

home = Path(os.environ["MPT_HOME"]).expanduser()
source = Path(os.environ["MPT_SOURCE_DIR"]).expanduser()
template = source / "config.example.toml"
if not template.is_file():
    raise SystemExit(f"MoneyPrinterTurbo config template not found: {template}")

gemini = os.environ.get("GEMINI_API_KEY", "").strip()
gemini_free_tier_enabled = os.environ.get("GEMINI_FREE_TIER_ENABLED", "true").strip().lower() == "true"
gemini_free_ready = bool(gemini and gemini_free_tier_enabled)
cloudflare_account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
cloudflare_api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
cloudflare_model = os.environ.get("CLOUDFLARE_MODEL", "@cf/zai-org/glm-4.7-flash").strip()
cloudflare_base_url = f"https://api.cloudflare.com/client/v4/accounts/{cloudflare_account_id}/ai/v1" if cloudflare_account_id else ""
cloudflare_ready = bool(cloudflare_account_id and cloudflare_api_token and cloudflare_model == "@cf/zai-org/glm-4.7-flash")
if cloudflare_account_id and cloudflare_api_token and not cloudflare_ready:
    print("Cloudflare model is not on the pinned free-model allowlist; refusing it.")
freellmapi_base_url = (os.environ.get("FREELLMAPI_CLOUD_BASE_URL", "").strip() or os.environ.get("FREELLMAPI_BASE_URL", "").strip())
freellmapi_key = os.environ.get("FREELLMAPI_API_KEY", "").strip()
freellmapi_model = os.environ.get("FREELLMAPI_MODEL", "auto").strip() or "auto"
allow_nonfree_fallback = os.environ.get("ALLOW_NONFREE_LLM_FALLBACK", "false").strip().lower() == "true"
if freellmapi_base_url and freellmapi_key:
    try:
        free_models = discover_free_models(
            freellmapi_base_url, freellmapi_key, task="seo", preferred=freellmapi_model
        )
    except Exception as exc:
        free_models = []
        print(f"FreeLLMAPI model discovery failed: {exc}")
    if free_models:
        # MoneyPrinterTurbo does not expose per-request model failover. Prefer
        # the gateway's free-only router when available; otherwise use the
        # strongest discovered free text model.
        freellmapi_model = next(
            (model for model in free_models if model == "kilo-auto/free"),
            free_models[0],
        )
        print(f"MoneyPrinterTurbo auto-selected explicitly free model: {freellmapi_model}")
    else:
        print("No explicitly free FreeLLMAPI models discovered; refusing unknown-price models.")
        freellmapi_base_url = ""
        freellmapi_key = ""
openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
openrouter_base_url = "https://openrouter.ai/api/v1"
openrouter_model = os.environ.get("OPENROUTER_MODEL", "auto").strip() or "auto"
openrouter_free_models = []
if openrouter_key:
    try:
        openrouter_free_models = discover_free_models(
            openrouter_base_url, openrouter_key, task="seo", preferred=openrouter_model
        )
    except Exception as exc:
        print(f"OpenRouter free-model discovery failed: {exc}")
    if openrouter_free_models:
        openrouter_model = openrouter_free_models[0]
        print(f"MoneyPrinterTurbo selected verified OpenRouter free model: {openrouter_model}")
    else:
        print("No explicitly free OpenRouter models discovered; refusing paid or unknown-price routing.")
omniroute_base_url = os.environ.get("OMNIROUTE_BASE_URL", "").strip()
omniroute_key = os.environ.get("OMNIROUTE_API_KEY", "").strip()
omniroute_model = os.environ.get("OMNIROUTE_MODEL", "auto").strip() or "auto"
pexels = os.environ.get("PEXELS_API_KEY", "").strip()
pixabay = os.environ.get("PIXABAY_API_KEY", "").strip()
missing = []
if not cloudflare_ready and not (freellmapi_base_url and freellmapi_key) and not openrouter_free_models and not (
    gemini_free_ready or (allow_nonfree_fallback and omniroute_base_url and omniroute_key)
):
    missing.append("a verified-free LLM route: Cloudflare Workers AI, Gemini free tier (GEMINI_API_KEY + GEMINI_FREE_TIER_ENABLED=true), or an explicitly free gateway model")
if not pexels and not pixabay:
    missing.append("PEXELS_API_KEY or PIXABAY_API_KEY")
if missing:
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write("ready=false\n")
    print("Quality test skipped. Add GitHub Actions secrets: " + ", ".join(missing))
    raise SystemExit(0)

config = toml.load(str(template))
app = config.setdefault("app", {})
# MoneyPrinterTurbo v1.3.10 supports Gemini and OpenAI-compatible custom base URLs.
# Prefer Gemini 3.8 Flash Standard Free Tier when a key is present; never route to paid tiers.
if gemini_free_ready:
    app["llm_provider"] = "gemini"
    app["gemini_api_key"] = gemini
    app["gemini_model_name"] = os.environ.get("SEO_GEMINI_MODEL", "gemini-3.8-flash").strip()
elif freellmapi_base_url and freellmapi_key:
    app["llm_provider"] = "openai"
    app["openai_api_key"] = freellmapi_key
    app["openai_base_url"] = freellmapi_base_url.rstrip("/")
    app["openai_model_name"] = freellmapi_model
elif cloudflare_ready:
    app["llm_provider"] = "openai"
    app["openai_api_key"] = cloudflare_api_token
    app["openai_base_url"] = cloudflare_base_url
    app["openai_model_name"] = cloudflare_model
elif openrouter_free_models:
    app["llm_provider"] = "openai"
    app["openai_api_key"] = openrouter_key
    app["openai_base_url"] = openrouter_base_url
    app["openai_model_name"] = openrouter_model
elif allow_nonfree_fallback and omniroute_base_url and omniroute_key:
    app["llm_provider"] = "openai"
    app["openai_api_key"] = omniroute_key
    app["openai_base_url"] = omniroute_base_url.rstrip("/")
    app["openai_model_name"] = omniroute_model
else:
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write("ready=false\n")
    print("No explicitly free LLM route is available; skipping generation rather than risk paid inference.")
    raise SystemExit(0)
app["video_source"] = "pexels" if pexels else "pixabay"
app["pexels_api_keys"] = [pexels] if pexels else []
app["pixabay_api_keys"] = [pixabay] if pixabay else []
app["match_materials_to_script"] = True
# MoneyPrinterTurbo v1.3.10 ships default music sourced from YouTube videos.
# Disable BGM until an individually verified, licensed track is supplied.
app["bgm_type"] = ""
app["bgm_volume"] = 0
app["upload_post_enabled"] = False
app["upload_post_auto_upload"] = False

ui = config.setdefault("ui", {})
ui.update({
    "language": "en",
    "video_language": "en-US",
    "voice_mode": "tts",
    "voice_name": "en-US-GuyNeural",
    "subtitle_enabled": True,
    "subtitle_display_mode": "word_by_word",
    "subtitle_animation": "pop_spring",
    "subtitle_position": "bottom",
    "video_aspect_pexels": "9:16",
    "video_fit_mode": "cover",
    "bgm_type": "random",
    "bgm_volume": 0.12,
})

home.mkdir(parents=True, exist_ok=True)
target = home / "config.toml"
target.write_text(toml.dumps(config), encoding="utf-8")
target.chmod(0o600)
print(f"Configured MoneyPrinterTurbo in {home}")
selected_model = app.get("gemini_model_name") if app["llm_provider"] == "gemini" else app.get("openai_model_name", "unknown")
print(f"LLM: {app['llm_provider']} ({selected_model}) | footage: {app['video_source']} | TTS: Edge Neural | upload: disabled")
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
    output.write("ready=true\n")
    output.write("video_source=" + app["video_source"] + "\n")
