"""Standard-library helpers for safe, idempotent YouTube upload state."""
import hashlib
import json
from pathlib import Path


def load_upload_history(state_dir: Path) -> dict:
    path = state_dir / "upload_history.json"
    if not path.exists():
        return {"schema_version": 1, "uploads": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Could not read upload history safely: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("uploads"), dict):
        raise RuntimeError("Upload history is malformed; refusing to risk duplicate publication.")
    for key, entry in value["uploads"].items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            raise RuntimeError("Upload history contains a malformed record.")
        if entry.get("status") not in {"pending", "completed"}:
            raise RuntimeError(f"Upload history entry {key!r} has an invalid status.")
    return value


def save_upload_history(state_dir: Path, history: dict) -> None:
    if not isinstance(history, dict) or not isinstance(history.get("uploads"), dict):
        raise RuntimeError("Upload history must contain an uploads object.")
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / "upload_history.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def idempotency_key(mode: str, digest: str) -> str:
    if mode not in {"public", "private"}:
        raise ValueError("Upload mode must be public or private.")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest.lower()):
        raise ValueError("SHA-256 digest must be a 64-character hexadecimal string.")
    return f"{mode}:{digest.lower()}"
