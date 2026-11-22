# Free local renderer bridge (Automated Video Generator)

NexLev can export its **already validated, AI-authored** narration and visual
search terms into the MIT-licensed
[Automated Video Generator](https://github.com/itsPremkumar/Automated-Video-Generator)
input format. This gives NexLev a second rendering engine with free stock-media
fallbacks (Openverse, Wikimedia Commons and Internet Archive) and free
Edge-TTS narration.

## Important boundaries

- This bridge is a renderer adapter, **not an LLM provider**. It does not fix a
  failure to generate scripts in FreeLLMAPI/Cloudflare.
- It refuses records marked `local_template_fallback` and requires 120-145
  spoken words and 5-8 specific visual terms per Short.
- No paid API key is required for the default rendering path. Optional Pexels
  keys can improve footage relevance but are not required.
- Openverse media has individual Creative Commons license/attribution terms.
  Review and preserve attribution before public release.
- Edge-TTS is free to use but is a remote Microsoft service, not offline TTS.
  For fully local speech, configure the upstream project's Kokoro/Voicebox
  backend; note its additional model/runtime requirements.
- Rendering is not proof of factual accuracy, rights clearance, or YouTube
  publishing readiness. NexLev's Persian subtitle, duration, visual-uniqueness,
  and human-review gates remain required.

## Prerequisites

- Windows 10/11, macOS, or Linux
- Node.js 18+ and npm
- Python 3.8+
- The upstream Automated Video Generator repository cloned locally

Upstream setup and license:
- https://github.com/itsPremkumar/Automated-Video-Generator
- https://github.com/itsPremkumar/Automated-Video-Generator/blob/main/LICENSE
- https://github.com/itsPremkumar/Automated-Video-Generator/blob/main/docs/OPENVERSE.md

## Export a four-video batch

First run NexLev's approved content-generation stage and ensure
`seo_metadata.json` contains four AI-authored records. Then, from the NexLev
repository root:

```powershell
python scripts/export_avgen_batch.py --input seo_metadata.json --output avgen-input-scripts.json
```

Copy the generated file to the upstream engine's expected input path:

```powershell
Copy-Item .\avgen-input-scripts.json <PATH_TO_AUTOMATED_VIDEO_GENERATOR>\input\scripts\input-scripts.json -Force
```

In the upstream repository, install and render:

```powershell
npm ci
$env:OPENVERSE_ENABLED = "true"
$env:TTS_PROVIDER = "edge-tts"
npm run generate -- --batch --concurrency 1
```

Rendered files are written under the upstream project's `output/<job-id>/`
folders. Review all four outputs before using them. This first bridge does not
automatically import the rendered files into NexLev's YouTube uploader or
bypass NexLev's Persian-subtitle and quality checks.

## Tests

```powershell
python -m unittest tests.test_export_avgen_batch -v
python -m py_compile scripts/export_avgen_batch.py
```
