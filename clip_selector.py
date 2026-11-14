
import json
import re
from pathlib import Path

def select_clips(transcript, count=4):
    """
    Select candidate short-video segments from a timestamped transcript.
    Each segment should be reviewed before publishing.
    """

    lines = transcript.strip().splitlines()
    segments = []
    current = []

    for line in lines:
        if re.match(r"^\[?\d{1,2}:\d{2}", line):
            if current:
                segments.append(" ".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        segments.append(" ".join(current))

    candidates = []

    for segment in segments:
        match = re.search(r"(\d{1,2}):(\d{2})", segment)
        if not match:
            continue

        seconds = int(match.group(1)) * 60 + int(match.group(2))

        candidates.append({
            "start_seconds": seconds,
            "transcript": segment,
            "duration_target": 45
        })

    result = {
        "clips": candidates[:count],
        "needs_review": True
    }

    return result


if __name__ == "__main__":
    source = Path("transcript.txt")

    if not source.exists():
        print("transcript.txt not found")
    else:
        output = select_clips(source.read_text(encoding="utf-8"))
        Path("clips.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print("Clip candidates created.")
