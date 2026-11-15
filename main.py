import json
import subprocess
from pathlib import Path

from transcribe import transcribe_video
from viral_selector import select_clips
from narration import create_narration
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
            f"Source video is too short: {duration:.1f} seconds. Need at least 120 seconds."
        )
    clip_length = 40
    available = duration - clip_length
    starts = [round(available * i / 3, 2) for i in range(4)]
    return [
        {
            "start": start, "end": start + clip_length,
            "duration": clip_length, "text": "", "score": 0
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
    transcript = []

    if has_audio:
        print("STEP 1: Transcribing and translating source speech to English...")
        transcript = transcribe_video(video)
        Path("transcript.json").write_text(
            json.dumps(transcript, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        if transcript:
            clips = select_clips(transcript, count=4)

    if len(clips) != 4:
        raise RuntimeError(
            "Could not find four transcript-based clips. "
            "The narration workflow needs spoken source content; "
            "no silent fallback videos will be published."
        )

    Path("best_clips.json").write_text(
        json.dumps(clips, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    Path("output").mkdir(exist_ok=True)
    print("STEP 2: Creating English narration, captions and four Shorts...")

    for index, clip in enumerate(clips, start=1):
        voice, subtitles = create_narration(clip, index)
        output = f"output/short_{index:02d}.mp4"
        create_short(
            source=str(video),
            start=clip["start"],
            duration=clip["duration"],
            output=output,
            voice=voice,
            subtitles=subtitles
        )
        print("Created:", output)

    print("PIPELINE COMPLETED")


if __name__ == "__main__":
    run_pipeline("input.mp4")
