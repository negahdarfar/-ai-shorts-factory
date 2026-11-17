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
freellmapi_base_url = os.environ.get("FREELLMAPI_BASE_URL", "").strip()
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
omniroute_base_url = os.environ.get("OMNIROUTE_BASE_URL", "").strip()
omniroute_key = os.environ.get("OMNIROUTE_API_KEY", "").strip()
omniroute_model = os.environ.get("OMNIROUTE_MODEL", "auto").strip() or "auto"
pexels = os.environ.get("PEXELS_API_KEY", "").strip()
pixabay = os.environ.get("PIXABAY_API_KEY", "").strip()
missing = []
if not (freellmapi_base_url and freellmapi_key) and not (
    allow_nonfree_fallback and (
        gemini or (omniroute_base_url and omniroute_key)
    )
):
    missing.append("FreeLLMAPI with an explicitly free model (or set ALLOW_NONFREE_LLM_FALLBACK=true to permit other providers)")
if not pexels and not pixabay:
    missing.append("PEXELS_API_KEY or PIXABAY_API_KEY")
if missing:
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write("ready=false\n")
    print("Quality test skipped. Add GitHub Actions secrets: " + ", ".join(missing))
    raise SystemExit(0)

config = toml.load(str(template))
app = config.setdefault("app", {})
# MoneyPrinterTurbo v1.3.10 supports OpenAI-compatible custom base URLs.
# Prefer FreeLLMAPI when configured; otherwise use the existing Gemini fallback.
if freellmapi_base_url and freellmapi_key:
    app["llm_provider"] = "openai"
    app["openai_api_key"] = freellmapi_key
    app["openai_base_url"] = freellmapi_base_url.rstrip("/")
    app["openai_model_name"] = freellmapi_model
elif allow_nonfree_fallback and omniroute_base_url and omniroute_key:
    app["llm_provider"] = "openai"
    app["openai_api_key"] = omniroute_key
    app["openai_base_url"] = omniroute_base_url.rstrip("/")
    app["openai_model_name"] = omniroute_model
elif allow_nonfree_fallback and gemini:
    app["llm_provider"] = "gemini"
    app["gemini_api_key"] = gemini
    app["gemini_model_name"] = "gemini-3.8-flash"
else:
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write("ready=false\n")
    print("No explicitly free LLM route is available; skipping generation rather than risk paid inference.")
    raise SystemExit(0)
app["video_source"] = "pexels" if pexels else "pixabay"
app["pexels_api_keys"] = [pexels] if pexels else []
app["pixabay_api_keys"] = [pixabay] if pixabay else []
app["match_materials_to_script"] = True
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
print(f"LLM: {app['llm_provider']} ({freellmapi_model if freellmapi_base_url and freellmapi_key else omniroute_model if omniroute_base_url and omniroute_key else 'gemini-3.8-flash'}) | footage: {app['video_source']} | TTS: Edge Neural | upload: disabled")
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
    output.write("ready=true\n")
    output.write("video_source=" + app["video_source"] + "\n")
