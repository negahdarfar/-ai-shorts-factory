import json
from pathlib import Path


def build_attribution(metadata_path="source_metadata.json",
                      output_path="output/attribution.txt"):
    source = Path(metadata_path)
    if not source.exists():
        raise FileNotFoundError(
            "source_metadata.json is required to create attribution."
        )

    metadata = json.loads(source.read_text(encoding="utf-8"))
    lines = [
        "SOURCE ATTRIBUTION",
        "==================",
        f"Title: {metadata.get('title') or 'Not provided'}",
        f"Creator: {metadata.get('artist') or 'Not provided'}",
        f"Credit: {metadata.get('credit') or 'Not provided'}",
        f"License: {metadata.get('license') or 'Not provided'}",
        f"License URL: {metadata.get('license_url') or 'Not provided'}",
        f"Original source: {metadata.get('source_page') or 'Not provided'}",
        "",
        "This file records the source information supplied by Wikimedia Commons.",
        "Check the original file page and license terms before publishing.",
    ]

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Attribution saved: {destination}")


if __name__ == "__main__":
    build_attribution()
