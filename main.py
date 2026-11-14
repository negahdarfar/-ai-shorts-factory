import json
import subprocess
from pathlib import Path

from transcribe import transcribe_video
from viral_selector import select_clips
from video_editor import create_short


def get_video_info(video):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-show_entries", "stream=codec_type",
            "-of", "json", str(video)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    has_audio = any(
        stream.get("codec_type") == "audio"
        for stream in data.get("streams", [])
    )

    return duration, has_audio


def make_fallback_clips(duration):
    if duration < 120:
        raise RuntimeError(
            f"Source video is too short: {duration:.1f} seconds. "
            "Need at least 120 seconds."
        )

    clip_length = 40
    available = duration - clip_length
    starts = [
        round(available * i / 3, 2)
        for i in range(4)
    ]

    return [
        {
            "start": start,
            "end": start + clip_length,
            "duration": clip_length,
            "text": "",
            "score": 0
        }
        for start in starts
    ]


def run_pipeline(video_path):
    video = Path(video_path)

    if not video.exists():
        raise FileNotFoundError(video)

    duration, has_audio = get_video_info(video)

    print("Video duration:", duration)
    print("Audio available:", has_audio)

    clips = []

    if has_audio:
        print("STEP 1: Transcribing video...")
        transcript = transcribe_video(video)

        Path("transcript.json").write_text(
            json.dumps(transcript, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        if transcript:
            clips = select_clips(transcript, count=4)

    if len(clips) != 4:
        print("Using visual fallback clip selection...")
        clips = make_fallback_clips(duration)

    Path("best_clips.json").write_text(
        json.dumps(clips, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("STEP 2: Creating four Shorts...")
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
