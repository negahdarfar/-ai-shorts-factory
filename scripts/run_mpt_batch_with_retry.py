#!/usr/bin/env python3
"""Run each MoneyPrinterTurbo batch item independently with transient-error retries."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RETRYABLE_MARKERS = (
    "503 unavailable",
    "503 service unavailable",
    "service temporarily overloaded",
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


def attach_prebuilt_content(batch, seo_path):
    """Inject prebuilt narration and footage terms so MPT never calls an LLM."""
    if not seo_path.is_file():
        raise SystemExit(f"Missing content manifest: {seo_path}")
    records = json.loads(seo_path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != len(batch):
        raise SystemExit("Content manifest must contain one record per batch topic.")
    by_topic = {
        str(row.get("topic", "")).strip().casefold(): row
        for row in records if isinstance(row, dict)
    }
    enriched = []
    for index, item in enumerate(batch, 1):
        topic = str(item.get("video_subject", "")).strip()
        record = by_topic.get(topic.casefold())
        if not record:
            raise SystemExit(f"No prebuilt content record found for topic {index}: {topic}")
        script = str(record.get("video_script", "")).strip()
        terms = record.get("video_terms")
        if not 120 <= len(script.split()) <= 145 or not isinstance(terms, list) or len(terms) < 5:
            raise SystemExit(f"Prebuilt narration must contain 120-145 words and search terms must be complete for topic {index}.")
        prepared = dict(item)
        prepared["video_script"] = script
        prepared["video_terms"] = terms
        enriched.append(prepared)
        print(
            f"PREBUILT_CONTENT_ATTACHED {index}/{len(batch)} | "
            f"script_words={len(script.split())} | terms={len(terms)} | "
            f"source={record.get('content_source', 'unknown')}",
            flush=True,
        )
    return enriched


def validate_distinct_visual_terms(batch):
    """Require separate, topic-specific stock-footage searches for every Short."""
    import re
    term_sets = []
    for index, item in enumerate(batch, 1):
        terms = item.get("video_terms", [])
        normalized = {re.sub(r"[^a-z0-9 ]", "", str(term).lower()).strip() for term in terms}
        normalized.discard("")
        if len(normalized) < 5:
            raise SystemExit(f"Video {index} has fewer than five distinct visual search terms.")
        if any(len(term.split()) < 2 for term in normalized):
            raise SystemExit(f"Video {index} contains a vague one-word visual search term.")
        term_sets.append(normalized)
    for i in range(len(term_sets)):
        for j in range(i + 1, len(term_sets)):
            overlap = len(term_sets[i] & term_sets[j]) / max(1, len(term_sets[i] | term_sets[j]))
            if overlap > 0.20:
                raise SystemExit(f"Videos {i+1} and {j+1} have overly similar stock-footage searches (Jaccard={overlap:.2f}); refusing repetitive visuals.")

def task_output_dirs(tasks_root):
    if not tasks_root.is_dir():
        return {}
    output = {}
    for path in tasks_root.glob("**/final-*.mp4"):
        output.setdefault(path.parent.resolve(), []).append(path.resolve())
    return output


def run_one(item, index, total, video_source, attempts, delay, temp_dir, tasks_root):
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
        "--subtitle-display-mode", "sentence",
        "--subtitle-animation", "pop_spring",
        "--subtitle-position", "bottom",
        "--video-fit-mode", "cover",
        "--bgm-volume", "0",
        "--stop-at", "video",
    ]

    print(f"\n=== Topic {index}/{total}: {topic} ===", flush=True)
    for attempt in range(1, attempts + 1):
        before_dirs = set(task_output_dirs(tasks_root))
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

        after_outputs = task_output_dirs(tasks_root)
        created_dirs = set(after_outputs) - before_dirs
        if return_code == 0:
            if len(created_dirs) != 1:
                result["last_error"] = (
                    f"Expected exactly one new task output directory for topic {index}; "
                    f"found {len(created_dirs)}."
                )
                result["status"] = "failed"
                return result
            task_dir = next(iter(created_dirs))
            final_files = after_outputs[task_dir]
            if len(final_files) != 1:
                result["last_error"] = (
                    f"Expected exactly one final MP4 for topic {index}; found {len(final_files)}."
                )
                result["status"] = "failed"
                return result
            result["status"] = "succeeded"
            result["last_error"] = ""
            result["task_dir"] = task_dir.relative_to(tasks_root.resolve()).as_posix()
            result["output_file"] = final_files[0].relative_to(tasks_root.resolve()).as_posix()
            print(f"Topic {index} succeeded: {result['output_file']}", flush=True)
            return result

        # A failed attempt must not leave a partial final MP4 that could be mistaken for a valid batch item.
        for directory in created_dirs:
            shutil.rmtree(directory, ignore_errors=True)
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
    batch = attach_prebuilt_content(batch, batch_path.parent / "seo_metadata.json")
    validate_distinct_visual_terms(batch)

    attempts = max(1, min(5, args.max_attempts))
    delay = max(1, args.retry_delay_seconds)
    results = []
    tasks_root = Path(os.environ.get("MPT_HOME", "mpt-runtime")) / "storage" / "tasks"
    with tempfile.TemporaryDirectory(prefix="mpt-single-tasks-") as temp_dir:
        for index, item in enumerate(batch, 1):
            results.append(
                run_one(item, index, len(batch), args.video_source, attempts, delay, temp_dir, tasks_root)
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
