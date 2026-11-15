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
pexels = os.environ.get("PEXELS_API_KEY", "").strip()
pixabay = os.environ.get("PIXABAY_API_KEY", "").strip()
if not gemini:
    raise SystemExit("Missing GEMINI_API_KEY GitHub Secret.")
if not pexels and not pixabay:
    raise SystemExit("Add PEXELS_API_KEY or PIXABAY_API_KEY (free stock-footage API).")

config = toml.load(str(template))
config["llm_provider"] = "gemini"
config["gemini_api_key"] = gemini
config["video_source"] = "pexels" if pexels else "pixabay"
config["pexels_api_keys"] = [pexels] if pexels else []
config["pixabay_api_keys"] = [pixabay] if pixabay else []
config["match_materials_to_script"] = True
config["upload_post_enabled"] = False
config["upload_post_auto_upload"] = False

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
print(f"LLM: Gemini | footage: {config['video_source']} | TTS: Edge Neural | upload: disabled")
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
    output.write("video_source=" + config["video_source"] + "\n")
