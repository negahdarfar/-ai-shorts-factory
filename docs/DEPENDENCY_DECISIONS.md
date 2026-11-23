# Dependency and model decision record

Review date: 2026-11-23. This is a bounded review of the explicitly named candidate projects, not a claim that every GitHub repository was audited. Software licenses do not grant rights to model weights, training data, media assets, or generated voices.

## Selected for active workflows

| Component | Decision | License / version | Reason and constraints |
|---|---|---|---|
| MoneyPrinterTurbo | Selected for `short-video-studio` only | Upstream tag `v1.3.10`; MIT | Provides a complete topic-to-script, stock-footage, TTS and render path. The workflow installs this exact tag. Its many optional provider integrations are not permission to use paid services; this factory's configuration allows only explicitly free model routes. |
| FFmpeg / ffprobe | Selected in all three engines | System package; upstream codebase mainly LGPL-2.1+, optional GPL components | Reliable media assembly, probing and validation without an extra Python editing layer. The exact distro binary build and enabled codecs must be checked before redistribution; no FFmpeg binary is vendored here. |
| faster-whisper | Selected in `viral-video-studio` | Python dependency range in `viral_factory/requirements.txt`; MIT code | CPU/int8 transcription is integrated. Model files are downloaded separately and their model/data terms must be reviewed independently. CPU transcription is slower and requires disk/RAM. |

## Evaluated, not currently integrated as a required runtime

| Project | Project-code license (reviewed source) | Decision |
|---|---|---|
| `Zulko/moviepy` | MIT | Not added as another rendering layer; FFmpeg CLI already handles current render tasks. Reconsider only if timeline editing becomes materially easier. |
| `ggml-org/whisper.cpp` | MIT | Viable local transcription alternative, but not installed in the active workflow; Whisper model-weight terms remain separate. |
| `Breakthrough/PySceneDetect` | BSD-3-Clause | Suitable optional scene-cut analysis; not required for the current transcript-window pipeline. It adds OpenCV/runtime resources and does not establish copyright permission. |
| `ollama/ollama` | MIT | Suitable local model runner, but not activated in the hosted workflows. Downloaded models have independent licenses and substantial storage/RAM/VRAM requirements. |
| `ggml-org/llama.cpp` | MIT | Suitable local inference runtime; not activated. Model weights and quantizations need independent license review and hardware sizing. |
| Kokoro TTS | Kokoro-82M model card states Apache-2.0 for that model | Not activated. The exact model revision, voice/training-data terms and runtime license must be checked before production use. |
| Piper TTS | Current OHF-Voice Piper engine is GPL-3.0-or-later | Not activated. Every voice model has its own license/model card; engine license does not grant voice rights. |

## Media and external-service rules

- Wikimedia Commons: each asset is accepted only after checking the per-file license label and URL; NC, ND, unknown and ShareAlike are rejected by the current viral engine. Commons metadata is not independent legal verification.
- Pexels/Pixabay: API access and per-asset license/terms must be checked separately; an API key does not grant blanket rights to every asset.
- Openverse: discovery only; the original source and exact asset license must be checked before download/use.
- YouTube Data API: public metadata is a research signal only. It is not a license to download, clip, dub or republish a creator's video.
- No paid or unknown-price provider may be silently selected. Missing free credentials/models should cause a clear skip/failure, not a paid upgrade.
- Free software does not make compute, runner time, model downloads, bandwidth, storage or electricity free.

## Versioning and reproducibility gaps

- MoneyPrinterTurbo is pinned to tag `v1.3.10`.
- The Viral engine's Python requirements currently use version ranges rather than a complete hash-locked dependency file. A reproducible lockfile and SBOM remain outstanding.
- Whisper and local LLM/TTS weights are not bundled or auto-downloaded by this review; users must inspect their license and resource requirements before enabling them.
- The `koroush_core/quality.py` source is byte-identical across the three specialist branches at the time of review, but there is no separately published shared-core package or immutable package pin. Cross-branch shared-core packaging is therefore still an architectural gap; the branches were not force-synchronized.
