#!/usr/bin/env python3
"""Merge durable repository state and the Actions runtime cache without losing upload guards."""
import argparse
import json
from pathlib import Path


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"State file is unreadable; refusing to overwrite it: {path}: {exc}") from exc


def merge_topics(left, right, label):
    if not isinstance(left, list) or not isinstance(right, list):
        raise SystemExit(f"{label} must be JSON arrays.")
    output = []
    seen = set()
    for value in left + right:
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"{label} contains an invalid topic.")
        key = value.strip().casefold()
        if key not in seen:
            seen.add(key)
            output.append(value.strip())
    return output


def freshness(entry):
    return str(entry.get("completed_at") or entry.get("started_at") or "")


def merge_uploads(left, right):
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise SystemExit("Upload ledger must contain an uploads object.")
    merged = dict(left)
    for key, candidate in right.items():
        if not isinstance(key, str) or not isinstance(candidate, dict):
            raise SystemExit("Upload ledger contains an invalid entry.")
        status = candidate.get("status")
        if status not in {"pending", "completed"}:
            raise SystemExit(f"Upload ledger entry {key!r} has an invalid status.")
        current = merged.get(key)
        if current is None:
            merged[key] = candidate
            continue
        if not isinstance(current, dict) or current.get("status") not in {"pending", "completed"}:
            raise SystemExit(f"Existing upload ledger entry {key!r} is malformed.")
        if current.get("status") == "completed" and status == "pending":
            continue
        if status == "completed" and current.get("status") == "pending":
            merged[key] = candidate
            continue
        if freshness(candidate) >= freshness(current):
            merged[key] = candidate
    return merged


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--durable", required=True)
    parser.add_argument("--direction", choices=("both", "to-runtime", "to-durable"), default="both")
    args = parser.parse_args()
    runtime = Path(args.runtime)
    durable = Path(args.durable)

    files = ("seen_topics.json", "published_topics.json")
    merged_lists = {}
    for name in files:
        merged_lists[name] = merge_topics(
            read_json(durable / name, []),
            read_json(runtime / name, []),
            name,
        )

    durable_ledger = read_json(durable / "upload_history.json", {"schema_version": 1, "uploads": {}})
    runtime_ledger = read_json(runtime / "upload_history.json", {"schema_version": 1, "uploads": {}})
    if not isinstance(durable_ledger, dict) or not isinstance(runtime_ledger, dict):
        raise SystemExit("Upload ledger root must be an object.")
    uploads = merge_uploads(durable_ledger.get("uploads", {}), runtime_ledger.get("uploads", {}))
    merged_ledger = {"schema_version": 1, "uploads": uploads}

    destinations = []
    if args.direction in {"both", "to-runtime"}:
        destinations.append(runtime)
    if args.direction in {"both", "to-durable"}:
        destinations.append(durable)
    for destination in destinations:
        for name, value in merged_lists.items():
            write_json(destination / name, value)
        write_json(destination / "upload_history.json", merged_ledger)

    print(
        f"FACTORY_STATE_MERGED topics_seen={len(merged_lists['seen_topics.json'])} "
        f"topics_published={len(merged_lists['published_topics.json'])} uploads={len(uploads)} "
        f"destinations={len(destinations)}"
    )


if __name__ == "__main__":
    main()
