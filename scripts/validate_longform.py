#!/usr/bin/env python3
"""Fail-closed validation for rendered 10–30 minute documentary videos."""
import argparse
import json
from pathlib import Path

from koroush_core.quality import QualityError, validate_media


def validate_longform(path: str, min_duration: float = 600.0) -> dict:
    if not 600 <= min_duration <= 1800:
        raise QualityError("Long-form minimum duration must be between 600 and 1800 seconds.")
    report = validate_media(
        path,
        min_duration=min_duration,
        max_duration=1800,
        aspect="16:9",
        require_audio=True,
    )
    if report["width"] < 1280 or report["height"] < 720:
        raise QualityError("Long-form output must be at least 1280x720.")
    report["profile"] = "longform-16x9"
    report["quality_gate"] = "passed"
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--min-duration-seconds", type=float, default=600.0)
    parser.add_argument("--report", default="longform-qa-report.json")
    args = parser.parse_args()
    try:
        report = validate_longform(args.input, args.min_duration_seconds)
    except (QualityError, OSError, ValueError) as exc:
        raise SystemExit(f"LONGFORM_QA_FAILED: {exc}") from exc
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("LONGFORM_QA_PASSED")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
