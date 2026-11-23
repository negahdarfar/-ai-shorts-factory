# KOROUSH — Short Video Studio

Independent English-language YouTube short-video pipeline.

## Current implementation
- MoneyPrinterTurbo v1.3.10 is installed from its upstream tag by the production workflow.
- Topic discovery, competitor metadata research, SEO metadata, thumbnail drafts and output validation.
- The workflow requests 4–10 videos per batch. The final media validator now requires 60–120 seconds and vertical 9:16 output (minimum 720×1280; 1080×1920 is the preferred target).
- English captions are supplied by the upstream render; Persian translation is saved as separate UTF-8 SRT and VTT sidecars. The subtitle script no longer burns Persian text into the MP4.
- This specialist branch's scheduled step uploads PRIVATE QA items only. However, the active default-branch workflow on `main` still contains a daily schedule for staggered PUBLIC release. The observed 2026-11-22 run failed at SEO metadata generation before upload, but a later run could reach the public scheduling step. `main` was not modified pending your approval.
- Upload history uses SHA-256 idempotency records and refuses ambiguous pending uploads.

## Workflow and scheduling boundary
- `.github/workflows/moneyprinterturbo.yml` — manual production and private scheduled QA.
- `.github/workflows/daily-factory-orchestrator.yml` — manual/scheduled dispatch coordinator.
- GitHub Actions scheduled workflows run only when the workflow file exists on the repository's default branch (`main`). This branch-specific workflow file does not independently establish a working daily schedule. Enabling scheduling requires an approved change to `main`; no such change has been made.
- No public upload was run during this work.

## Local validation
Install Python 3.11, FFmpeg, fonts and the repository requirements, then run:
```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/validate_mpt_outputs.py
```
The last command requires a completed MoneyPrinterTurbo batch and its runtime reports; it is not a standalone sample render.

## Known limits
- Actual MoneyPrinterTurbo generation and its ability to meet the new 60–120 second gate have not yet been proven by a real render.
- Separate SRT/VTT sidecars are generated locally, but YouTube caption-track upload is not yet implemented/verified. Existing OAuth scope `youtube.upload` alone does not prove caption API permission.
- The main-branch public schedule remains a live risk until explicitly disabled. The specialist-branch public input is manual-only.
- Free software does not eliminate runner, bandwidth, model-download, storage or electricity costs.
