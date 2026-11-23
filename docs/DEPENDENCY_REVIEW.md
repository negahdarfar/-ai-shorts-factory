# Dependency and model-license review — 2026-11-23

This is a scoped review of the candidate projects named in the factory brief, not a claim that every GitHub repository was audited. Repository metadata was checked on 2026-11-23. A repository's software license does not automatically license downloaded model weights, voices, datasets, media, or generated outputs.

| Candidate | Repository license / status observed | Decision in this factory |
|---|---|---|
| [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) | MIT; active; workflow pins upstream tag `v1.3.10` | Used by Short Video Studio. Upstream tag does not pin all transitive Python packages, TTS voices, or media rights. |
| [FFmpeg](https://github.com/FFmpeg/FFmpeg) | GitHub API reports `NOASSERTION`; active | Used as an external system executable. FFmpeg can be LGPL or GPL depending on build flags and linked libraries. The Ubuntu runner binary's exact configure flags/SBOM have not been audited; do not infer a single license from the repository label. |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT; active | Used by Viral Video Studio. Model weights downloaded by CTranslate2 are separate assets and require their own license review. |
| [MoviePy](https://github.com/Zulko/moviepy) | MIT; active | Not selected: current render paths already use FFmpeg directly; adding another editing layer would increase dependencies without a demonstrated need. |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | MIT; active | Not selected: faster-whisper is already integrated. It remains a possible local alternative, not a current fallback. |
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | BSD-3-Clause; active | Not selected yet: current clip windows are transcript-boundary based. Scene detection is not required for the present pipeline. |
| [Ollama](https://github.com/ollama/ollama) | MIT; active | Optional local HTTP provider path exists in parts of the short pipeline, but Ollama is not installed by GitHub Actions and no model is bundled. |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | MIT; active | Not directly integrated; could be hosted locally behind a compatible endpoint. Model GGUF files have separate licenses. |
| [Kokoro](https://github.com/hexgrad/kokoro) | Apache-2.0 repository; last repository push observed 2025-08-06 | Not integrated. The model/voice weights and any voice-specific usage terms were not independently verified, so no Kokoro model is downloaded or used. |
| [Piper](https://github.com/rhasspy/piper) | MIT repository; archived | Not selected. Archived upstream is not an appropriate default dependency for a new actively maintained path; individual voice models also have separate licenses. |

## Current pinning and supply-chain gaps

- Python target in workflows: 3.11.
- MoneyPrinterTurbo upstream: tag `v1.3.10`.
- Viral engine declares `faster-whisper>=1.1,<2` and bounded Google API dependencies, not exact lock hashes.
- Root `requirements.txt` files are currently unpinned (`yt-dlp`, `faster-whisper`, `Pillow`, `numpy`).
- FFmpeg is installed from the runner's apt repositories without an exact package version or recorded configure flags.
- Long-form narration currently installs `edge-tts` at workflow runtime without an exact pin. Edge voices are a hosted service, not a fully local TTS model.
- No dependency lockfile with hashes, container digest, FFmpeg build manifest, model checksum/license manifest, or SBOM is currently enforced.

## Operational decision

No unverified TTS model or model weights were added. The current safe path keeps FFmpeg rendering, MoneyPrinterTurbo's pinned source tag, and Faster-Whisper; it does not silently switch to a paid provider. Free software still requires compute, storage, network bandwidth, electricity, and sometimes quota-limited API access.

## Remaining work before production sign-off

1. Pin all Python dependencies exactly and generate a hash-verified lock file per engine.
2. Pin the FFmpeg package/build and archive `ffmpeg -buildconf` output plus a license/SBOM report.
3. Record SHA-256 and model-license metadata for every downloaded ASR/TTS model.
4. Verify the license terms for each individual voice/model checkpoint before commercial use.
5. Test each fallback provider's actual free-tier/quota behavior; a provider name or `free` model suffix is not a guarantee of zero cost.
