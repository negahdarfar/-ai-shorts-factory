#!/usr/bin/env python3
"""Persistent topic history helpers shared by discovery and YouTube publishing."""
import json
from pathlib import Path


def _read_list(path: Path, label: str) -> list[str]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Could not read {label} safely: {exc}") from exc
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise RuntimeError(f"{label} is malformed; expected a JSON array of non-empty strings.")
    return value


def load_seen_topics(state_dir: Path) -> set[str]:
    return {item.casefold() for item in _read_list(state_dir / "seen_topics.json", "topic history")}


def load_published_topics(state_dir: Path) -> set[str]:
    return {item.casefold() for item in _read_list(state_dir / "published_topics.json", "publication history")}


def ensure_new_topics(state_dir: Path, topics: list[str]) -> None:
    published = load_published_topics(state_dir)
    duplicates = [topic for topic in topics if topic.strip().casefold() in published]
    if duplicates:
        raise RuntimeError(
            "PUBLIC_PUBLISH_BLOCKED_DUPLICATE_TOPICS: "
            + "; ".join(duplicates)
            + ". Choose four new topics or run private QA."
        )


def _append_unique(path: Path, topic: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current = _read_list(path, label)
    if topic.strip().casefold() not in {item.casefold() for item in current}:
        current.append(topic.strip())
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")


def record_seen_topics(state_dir: Path, topics: list[str]) -> None:
    for topic in topics:
        _append_unique(state_dir / "seen_topics.json", topic, "topic history")


def record_published_topic(state_dir: Path, topic: str) -> None:
    _append_unique(state_dir / "published_topics.json", topic, "publication history")
