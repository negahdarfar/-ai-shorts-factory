#!/usr/bin/env python3
"""Run each MoneyPrinterTurbo batch item independently with transient-error retries."""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RETRYABLE_MARKERS = (
    "503 unavailable",
    "500 internal",
    "502 bad gateway",
    "504 gateway timeout",
    "temporarily unavailable",
    "currently experiencing high demand",
    "rate limit exceeded",
    "429 too many requests",
)


def is_retryable(output):
    lowered = output.lower()
    return any(marker in lowered for marker in RETRYABLE_MARKERS)


def run_one(item, index, total, video_source, attempts, delay, temp_dir):
    topic = item.get("video_subject", f"item-{index}")
    result = {"index": index, "topic": topic, "status": "failed", "attempts": 0, "last_error": ""}
    manifest = Path(temp_dir) / f"item-{index:02d}.json"
    manifest.write_text(json.dumps([item], ensure_ascii=False, indent=2), encoding="utf-8")

    command = [
        "mpt", "cli", "--batch-file", str(manifest),
        "--video-source", video_source,
        "--video-aspect", "9:16",
        "--video-language", "en-US",
        "--voice-name", "en-US-GuyNeural",
        "--subtitle-enabled",
        "--subtitle-display-mode", "word_by_word",
        "--subtitle-animation", "pop_spring",
        "--subtitle-position", "bottom",
        "--video-fit-mode", "cover",
        "--bgm-volume", "0.12",
        "--stop-at", "video",
    ]

    print(f"\n=== Topic {index}/{total}: {topic} ===", flush=True)
    for attempt in range(1, attempts + 1):
        result["attempts"] = attempt
        print(f"Attempt {attempt}/{attempts}", flush=True)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        captured = []
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            captured.append(line)
        return_code = process.wait()
        output = "".join(captured)

        if return_code == 0:
            result["status"] = "succeeded"
            result["last_error"] = ""
            print(f"Topic {index} succeeded.", flush=True)
            return result

        result["last_error"] = output[-6000:]
        if attempt < attempts and is_retryable(output):
            wait_seconds = delay * (2 ** (attempt - 1))
            print(
                f"Transient provider error for topic {index}; retrying in {wait_seconds}s.",
                flush=True,
            )
            time.sleep(wait_seconds)
            continue

        if not is_retryable(output):
            print(f"Topic {index} failed with a non-retryable error.", flush=True)
        else:
            print(f"Topic {index} exhausted {attempts} attempts.", flush=True)
        return result

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-file", required=True)
    parser.add_argument("--video-source", choices=("pexels", "pixabay"), required=True)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=int, default=20)
    args = parser.parse_args()

    batch_path = Path(args.batch_file).resolve()
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    if not isinstance(batch, list) or not batch:
        raise SystemExit("Batch manifest must be a non-empty JSON array.")

    attempts = max(1, min(5, args.max_attempts))
    delay = max(1, args.retry_delay_seconds)
    results = []
    with tempfile.TemporaryDirectory(prefix="mpt-single-tasks-") as temp_dir:
        for index, item in enumerate(batch, 1):
            results.append(
                run_one(item, index, len(batch), args.video_source, attempts, delay, temp_dir)
            )

    report = {
        "total": len(results),
        "succeeded": sum(row["status"] == "succeeded" for row in results),
        "failed": sum(row["status"] != "succeeded" for row in results),
        "retry_policy": {"max_attempts": attempts, "initial_delay_seconds": delay},
        "tasks": results,
    }
    report_path = batch_path.parent / "batch_retry_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nBatch retry summary:")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
