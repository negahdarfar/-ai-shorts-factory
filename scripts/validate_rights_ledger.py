#!/usr/bin/env python3
"""Fail-closed rights ledger validation for long-form source assets."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse


class RightsError(ValueError):
    """Raised when a source asset lacks sufficient rights metadata."""


def _normalise_license(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower().replace("_", " ").replace("-", " "))


def _license_family(value: str) -> str | None:
    text = _normalise_license(value)
    if re.search(r"\bcc by nc\b|\bcc by nd\b|\bnoncommercial\b|\bno derivatives\b", text):
        return None
    if text in {"public domain", "publicdomain", "pd", "cc0", "cc0 1.0"} or text.startswith("cc0 "):
        return "public-domain"
    if re.match(r"^cc by sa(?:\s|$)", text):
        return "cc-by-sa"
    if re.match(r"^cc by(?:\s|$)", text):
        return "cc-by"
    if text in {"owned", "original", "user owned", "user-owned", "all rights owned"}:
        return "owned"
    return None


def validate_rights_ledger(manifest_path: str | Path, ledger_path: str | Path) -> dict:
    manifest_file = Path(manifest_path).resolve()
    ledger_file = Path(ledger_path).resolve()
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RightsError(f"Cannot read manifest or rights ledger: {exc}") from exc
    if not isinstance(manifest, list) or not manifest:
        raise RightsError("Clip manifest must be a non-empty JSON array.")
    if not isinstance(ledger, list):
        raise RightsError("Rights ledger must be a JSON array.")

    required = {str(Path(item).as_posix()) for item in manifest if isinstance(item, str) and item.strip()}
    if len(required) != len(manifest):
        raise RightsError("Every manifest item must be a non-empty relative asset path.")
    if any(Path(item).is_absolute() or ".." in Path(item).parts for item in required):
        raise RightsError("Manifest asset paths must be relative and cannot traverse parent directories.")

    entries: dict[str, dict] = {}
    for index, item in enumerate(ledger):
        if not isinstance(item, dict):
            raise RightsError(f"Ledger entry {index} must be an object.")
        asset = item.get("asset")
        if not isinstance(asset, str) or not asset.strip():
            raise RightsError(f"Ledger entry {index} has no asset path.")
        asset = Path(asset).as_posix()
        if asset in entries:
            raise RightsError(f"Duplicate rights ledger entry for asset: {asset}")
        entries[asset] = item

    missing = sorted(required - set(entries))
    if missing:
        raise RightsError("Missing rights records for: " + ", ".join(missing))
    unused = sorted(set(entries) - required)
    if unused:
        raise RightsError("Ledger contains assets not present in the clip manifest: " + ", ".join(unused))

    validated = []
    for asset in sorted(required):
        item = entries[asset]
        family = _license_family(item.get("license", ""))
        if family is None:
            raise RightsError(f"Unsupported or unclear license for {asset}.")
        for field in ("source_url", "license_url"):
            value = item.get(field, "")
            parsed = urlparse(value) if isinstance(value, str) else None
            if parsed is None or parsed.scheme != "https" or not parsed.netloc:
                raise RightsError(f"{asset} requires a valid HTTPS {field}.")
        if not isinstance(item.get("attribution"), str) or not item["attribution"].strip():
            raise RightsError(f"{asset} requires attribution text (use an explicit public-domain/source credit if applicable).")
        if family == "cc-by-sa" and item.get("share_alike_acknowledged") is not True:
            raise RightsError(f"{asset} uses CC BY-SA; set share_alike_acknowledged to true only after confirming ShareAlike compliance.")
        if family == "owned" and (not isinstance(item.get("rights_holder"), str) or not item.get("rights_holder", "").strip()):
            raise RightsError(f"{asset} marked owned requires a named rights_holder.")
        validated.append({"asset": asset, "license_family": family})

    return {
        "profile": "longform-rights-ledger",
        "rights_gate": "passed",
        "assets_checked": len(validated),
        "assets": validated,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--report", default="rights-qa-report.json")
    args = parser.parse_args()
    try:
        report = validate_rights_ledger(args.manifest, args.ledger)
    except RightsError as exc:
        raise SystemExit(f"RIGHTS_QA_FAILED: {exc}") from exc
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("RIGHTS_QA_PASSED")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
