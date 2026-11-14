
import json
import urllib.request
import urllib.parse
from pathlib import Path

CANDIDATES_FILE = Path("source_candidates.json")
OUTPUT_FILE = Path("input.mp4")
METADATA_FILE = Path("source_metadata.json")

MAX_SIZE = 500 * 1024 * 1024

USER_AGENT = "ViralNovaLabsShortsFactory/1.0"


def download_candidate(item):
    url = item.get("download_url", "")

    parsed = urllib.parse.urlparse(url)

    if parsed.scheme != "https":
        raise ValueError("Only HTTPS sources are allowed")

    if parsed.hostname not in {
        "upload.wikimedia.org",
        "commons.wikimedia.org"
    }:
        raise ValueError("Untrusted download host")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )

    temporary_file = Path("input_download.tmp")

    try:
        print("Downloading:", item.get("title", "Unknown"))

        with urllib.request.urlopen(request, timeout=90) as response:
            content_type = response.headers.get("Content-Type", "")

            if not (
                content_type.startswith("video/")
                or "octet-stream" in content_type
            ):
                raise ValueError(
                    "Unexpected content type: " + content_type
                )

            total = 0

            with temporary_file.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)

                    if not chunk:
                        break

                    total += len(chunk)

                    if total > MAX_SIZE:
                        raise ValueError("Video exceeds 500 MB limit")

                    output.write(chunk)

        if total == 0:
            raise ValueError("Downloaded file is empty")

        temporary_file.replace(OUTPUT_FILE)

        metadata = {
            "title": item.get("title"),
            "source_page": item.get("source_page"),
            "download_url": url,
            "license": item.get("license"),
            "license_url": item.get("license_url"),
            "artist": item.get("artist"),
            "credit": item.get("credit"),
            "description": item.get("description"),
            "downloaded_file": str(OUTPUT_FILE),
            "file_size_bytes": total
        }

        METADATA_FILE.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print("Download completed:", total, "bytes")
        return True

    finally:
        if temporary_file.exists():
            temporary_file.unlink()


def main():
    if not CANDIDATES_FILE.exists():
        raise FileNotFoundError(
            "source_candidates.json not found. Run source_discovery.py first."
        )

    candidates = json.loads(
        CANDIDATES_FILE.read_text(encoding="utf-8")
    )

    if not candidates:
        raise RuntimeError("No video candidates available.")

    for item in candidates:
        try:
            if download_candidate(item):
                print("SOURCE READY")
                return
        except Exception as error:
            print("Candidate skipped:", error)

    raise RuntimeError("Could not download any eligible video.")


if __name__ == "__main__":
    main()
