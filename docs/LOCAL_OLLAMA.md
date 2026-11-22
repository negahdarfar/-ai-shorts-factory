# Local Ollama runtime (no paid LLM API)

NexLev can use a local Ollama server for narration/SEO generation and Persian subtitle translation. Requests stay on the computer running Ollama; this does not expose a public endpoint and does not require an API key.

## Recommended starter model

For a Windows PC with 16 GB RAM and an NVIDIA GPU with 4 GB VRAM, start with the small quantized model:

```powershell
# Install Ollama for Windows first, then:
ollama pull qwen2.5:3b
ollama list
```

The model may use system RAM when it does not fit entirely in VRAM. Generation can be slower on a 4 GB GPU. Do not start by downloading 7B/14B models.

## Run NexLev locally

Keep Ollama bound to localhost (default `http://127.0.0.1:11434`). Do not port-forward 11434 or expose it to the public internet.

```powershell
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
$env:OLLAMA_MODEL = "qwen2.5:3b"
python scripts/generate_seo_metadata.py --input trending_batch.json --output seo_metadata.json --require-ai-batch
```

The existing validation still applies: each narration must be 120–145 words and all required SEO fields must be valid. `--require-ai-batch` makes the command fail instead of treating local template fallback as publishable content.

For Persian subtitles, run the existing four-video subtitle stage on the same PC after English SRT files exist:

```powershell
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
$env:OLLAMA_MODEL = "qwen2.5:3b"
python scripts/add_persian_subtitles.py --home mpt-runtime
```

Ollama is tried first for subtitles; configured fallback providers are considered only if local translation fails and their existing policy permits it. Cue indices and timestamps remain validated by the current subtitle pipeline.

## Architecture and limits

- GitHub-hosted Actions runners cannot reach Ollama on your private PC at `127.0.0.1`. Run the generation/rendering stages on the Windows PC (or a self-hosted runner on that PC).
- This integration does not install Ollama, download the model, render a video, upload to YouTube, or enable public publishing.
- Keep the public-upload gate closed until all four videos pass visual, factual, subtitle, rights/attribution, and audio checks.
- Ollama software is free/open source; model licenses and usage terms vary by model. Verify the selected model's license before commercial use.
