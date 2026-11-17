#!/usr/bin/env python3
"""Create a private MoneyPrinterTurbo config from GitHub Actions secrets."""
import os
from pathlib import Path
import toml

home = Path(os.environ["MPT_HOME"]).expanduser()
source = Path(os.environ["MPT_SOURCE_DIR"]).expanduser()
template = source / "config.example.toml"
if not template.is_file():
    raise SystemExit(f"MoneyPrinterTurbo config template not found: {template}")

gemini = os.environ.get("GEMINI_API_KEY", "").strip()
freellmapi_base_url = os.environ.get("FREELLMAPI_BASE_URL", "").strip()
freellmapi_key = os.environ.get("FREELLMAPI_API_KEY", "").strip()
freellmapi_model = os.environ.get("FREELLMAPI_MODEL", "auto").strip() or "auto"
omniroute_base_url = os.environ.get("OMNIROUTE_BASE_URL", "").strip()
omniroute_key = os.environ.get("OMNIROUTE_API_KEY", "").strip()
omniroute_model = os.environ.get("OMNIROUTE_MODEL", "auto").strip() or "auto"
pexels = os.environ.get("PEXELS_API_KEY", "").strip()
pixabay = os.environ.get("PIXABAY_API_KEY", "").strip()
missing = []
if not gemini and not (freellmapi_base_url and freellmapi_key) and not (omniroute_base_url and omniroute_key):
    missing.append("FreeLLMAPI or OmniRoute credentials, or GEMINI_API_KEY")
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
elif omniroute_base_url and omniroute_key:
    app["llm_provider"] = "openai"
    app["openai_api_key"] = omniroute_key
    app["openai_base_url"] = omniroute_base_url.rstrip("/")
    app["openai_model_name"] = omniroute_model
else:
    app["llm_provider"] = "gemini"
    app["gemini_api_key"] = gemini
    app["gemini_model_name"] = "gemini-3.8-flash"
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
