
import json
import time
import urllib.error
import urllib.request
import urllib.parse
import subprocess
from pathlib import Path

CANDIDATES_FILE = Path("source_candidates.json")
OUTPUT_FILE = Path("input.mp4")
METADATA_FILE = Path("source_metadata.json")

MAX_SIZE = 500 * 1024 * 1024
MIN_DURATION = 120

USER_AGENT = (
    "ViralNovaLabsShortsFactory/1.2 "
    "(https://github.com/negahdarfar/-ai-shorts-factory)"
)


def open_with_backoff(request, timeout, attempts=4):
    delay = 10

    for attempt in range(1, attempts + 1):
        try:
            return urllib.request.urlopen(request, timeout=timeout)

        except urllib.error.HTTPError as error:
            if error.code not in (429, 503):
                raise

            retry_after = error.headers.get("Retry-After")

            try:
                wait_seconds = (
                    max(delay, int(retry_after))
                    if retry_after else delay
                )
            except ValueError:
                wait_seconds = delay

            if attempt == attempts:
                raise RuntimeError(
                    f"Rate limited after {attempts} attempts."
                ) from error

            print(f"Rate limited. Waiting {wait_seconds}s...")
            error.close()
            time.sleep(wait_seconds)
            delay = min(delay * 2, 120)


def get_duration(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    return float(result.stdout.strip())


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

        with open_with_backoff(request, timeout=120) as response:
            content_type = response.headers.get(
                "Content-Type", ""
            )

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
                        raise ValueError(
                            "Video exceeds 500 MB limit"
                        )

                    output.write(chunk)

        if total == 0:
            raise ValueError("Downloaded file is empty")

        duration = get_duration(temporary_file)

        print("Actual video duration:", duration)

        if duration < MIN_DURATION:
            raise ValueError(
                f"Video too short: {duration:.1f}s. "
                f"Minimum is {MIN_DURATION}s."
            )

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
            "duration_seconds": duration,
            "downloaded_file": str(OUTPUT_FILE),
            "file_size_bytes": total
        }

        METADATA_FILE.write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        print("Valid source downloaded successfully.")
        return True

    finally:
        if temporary_file.exists():
            temporary_file.unlink()


def main():
    if not CANDIDATES_FILE.exists():
        raise FileNotFoundError(
            "source_candidates.json not found."
        )

    candidates = json.loads(
        CANDIDATES_FILE.read_text(encoding="utf-8")
    )

    if not candidates:
        raise RuntimeError("No video candidates available.")

    candidates = sorted(
        candidates,
        key=lambda item: item.get("size", 0)
    )

    for index, item in enumerate(candidates, start=1):
        print(
            f"Candidate {index}/{len(candidates)}"
        )

        try:
            if download_candidate(item):
                print("SOURCE READY")
                return

        except RuntimeError as error:
            if "Rate limited" in str(error):
                raise

            print("Candidate skipped:", error)

        except Exception as error:
            print("Candidate skipped:", error)

    raise RuntimeError(
        "No downloaded video passed the 120-second duration check."
    )


if __name__ == "__main__":
    main()
