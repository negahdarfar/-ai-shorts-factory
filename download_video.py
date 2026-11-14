
import urllib.request
from pathlib import Path

def download_video(url):
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS download links are allowed")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AI-Shorts-Factory/1.0"}
    )

    print("Downloading authorized video...")

    with urllib.request.urlopen(request, timeout=60) as response:
        content_type = response.headers.get("Content-Type", "")

        if not content_type.startswith("video/"):
            raise ValueError(
                f"URL did not return a video: {content_type}"
            )

        with open("input.mp4", "wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)

    if Path("input.mp4").stat().st_size == 0:
        raise ValueError("Downloaded file is empty")

    print("Video download completed.")

if __name__ == "__main__":
    source_file = Path("video_sources.txt")

    urls = [
        line.strip()
        for line in source_file.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("https://")
    ]

    if not urls:
        raise ValueError("No authorized direct video URL found")

    download_video(urls[0])
