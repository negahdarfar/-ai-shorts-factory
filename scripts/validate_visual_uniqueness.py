#!/usr/bin/env python3
"""Detect near-duplicate footage across Shorts by comparing sampled video-frame hashes."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def difference_hash(image):
    """Return a 64-bit difference hash for a PIL image."""
    pixels = list(image.convert("L").resize((9, 8)).getdata())
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return value


def hamming_distance(left, right):
    return (left ^ right).bit_count()


def probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def sample_hashes(path, samples):
    duration = probe_duration(path)
    hashes = []
    with tempfile.TemporaryDirectory(prefix="shorts-frames-") as temp:
        for index in range(samples):
            # Avoid title-card/black-frame boundaries while covering the full story.
            timestamp = duration * (0.12 + 0.76 * index / max(1, samples - 1))
            target = Path(temp) / f"frame-{index}.jpg"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.3f}",
                 "-i", str(path), "-frames:v", "1", "-vf", "scale=96:54",
                 "-y", str(target)],
                capture_output=True, check=True
            )
            with Image.open(target) as frame:
                hashes.append(difference_hash(frame))
    return hashes


def matched_frame_pairs(left, right, max_distance):
    candidates = sorted(
        (hamming_distance(a, b), i, j)
        for i, a in enumerate(left)
        for j, b in enumerate(right)
        if hamming_distance(a, b) <= max_distance
    )
    used_left, used_right = set(), set()
    matches = []
    for distance, i, j in candidates:
        if i not in used_left and j not in used_right:
            used_left.add(i)
            used_right.add(j)
            matches.append({"left_frame": i + 1, "right_frame": j + 1, "hamming_distance": distance})
    return matches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", default=os.getenv("MPT_HOME", "mpt-runtime"))
    parser.add_argument("--expected-count", type=int, default=4)
    parser.add_argument("--samples", type=int, default=6)
    parser.add_argument("--max-hamming-distance", type=int, default=5)
    parser.add_argument("--minimum-matching-frames", type=int, default=2)
    parser.add_argument("--output", default="visual_uniqueness_report.json")
    args = parser.parse_args()
    if not 4 <= args.expected_count <= 10:
        raise SystemExit("--expected-count must be between 4 and 10.")

    root = Path(args.home) / "storage" / "tasks"
    files = sorted(root.glob("**/final-*.mp4"))
    if len(files) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} videos for visual comparison, found {len(files)}.")

    signatures = []
    for path in files:
        print(f"Sampling visual frames: {path.name}", flush=True)
        signatures.append((path, sample_hashes(path, max(3, args.samples))))

    comparisons = []
    failures = []
    for i in range(len(signatures)):
        for j in range(i + 1, len(signatures)):
            left_path, left_hashes = signatures[i]
            right_path, right_hashes = signatures[j]
            matches = matched_frame_pairs(left_hashes, right_hashes, args.max_hamming_distance)
            row = {
                "video_a": left_path.name,
                "video_b": right_path.name,
                "near_duplicate_frame_pairs": len(matches),
                "matches": matches,
                "status": "failed" if len(matches) >= args.minimum_matching_frames else "passed",
            }
            comparisons.append(row)
            if row["status"] == "failed":
                failures.append(row)
                print(f"VISUAL_DUPLICATION_RISK: {left_path.name} vs {right_path.name} ({len(matches)} matching frames)", flush=True)
            else:
                print(f"VISUAL_PAIR_PASS: {left_path.name} vs {right_path.name}", flush=True)

    report = {
        "method": "sampled-frame 64-bit difference-hash comparison",
        "samples_per_video": max(3, args.samples),
        "max_hamming_distance": args.max_hamming_distance,
        "minimum_matching_frames_to_fail": args.minimum_matching_frames,
        "videos": [path.name for path, _ in signatures],
        "comparisons": comparisons,
        "passed": not failures,
        "limitations": [
            "This detects repeated or near-identical sampled frames, not semantic similarity or every reused shot.",
            "Different crops, edits, overlays, color grading, or footage between sample timestamps can evade detection.",
            "A human review remains necessary for topic relevance and originality."
        ]
    }
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        raise SystemExit(f"Visual uniqueness check failed: {len(failures)} video pairs contain repeated-looking frames.")
    print(f"VISUAL_UNIQUENESS_PASS: all {len(signatures)} videos passed pairwise sampled-frame checks.")


if __name__ == "__main__":
    main()
