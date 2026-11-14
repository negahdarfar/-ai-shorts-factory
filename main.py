
import json
import subprocess
from pathlib import Path

from transcribe import transcribe_video
from viral_selector import select_clips
from video_editor import create_short

def run_pipeline(video_path):
    video = Path(video_path)

    if not video.exists():
        raise FileNotFoundError(video)

    print("STEP 1: Transcribing video...")

    transcript = transcribe_video(video)

    Path("transcript.json").write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("STEP 2: Selecting best clips...")

    clips = select_clips(transcript, count=4)

    Path("best_clips.json").write_text(
        json.dumps(clips, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("STEP 3: Creating shorts...")

    Path("output").mkdir(exist_ok=True)

    for index, clip in enumerate(clips, start=1):
        output = f"output/short_{index:02d}.mp4"

        create_short(
            source=str(video),
            start=clip["start"],
            duration=clip["duration"],
            output=output
        )

        print("Created:", output)

    print("PIPELINE COMPLETED")

if __name__ == "__main__":
    run_pipeline("input.mp4")
