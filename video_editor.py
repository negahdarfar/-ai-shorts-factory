
import subprocess
from pathlib import Path

def create_short(source, start, duration, output):
    source = str(source)
    output = str(output)

    command = [
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-i", source,
        "-t", str(duration),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output
    ]

    subprocess.run(command, check=True)

if __name__ == "__main__":
    video = Path("input.mp4")

    if not video.exists():
        print("input.mp4 not found")
        raise SystemExit(1)

    create_short(
        source=video,
        start=0,
        duration=45,
        output="short_01.mp4"
    )

    print("Short video created successfully.")
