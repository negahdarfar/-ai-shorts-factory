import json
import subprocess
from pathlib import Path


VOICE = "en_US-lessac-medium"
VOICE_DIR = Path("voices")


def srt_time(seconds):
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def make_caption_entries(clip, transcript):
    start = float(clip["start"])
    end = float(clip["end"])
    entries = []

    for segment in transcript:
        seg_start = max(start, float(segment["start"]))
        seg_end = min(end, float(segment["end"]))
        text = str(segment.get("text", "")).strip()
        if text and seg_end > seg_start:
            entries.append((seg_start - start, seg_end - start, text))

    if not entries:
        text = str(clip.get("text", "")).strip()
        if text:
            entries = [(0.0, float(clip["duration"]), text)]

    return entries


def create_narration(clip, index):
    transcript_path = Path("transcript.json")
    transcript = []
    if transcript_path.exists():
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))

    text = str(clip.get("text", "")).strip()
    if not text:
        overlapping = [
            item for item in transcript
            if float(item["end"]) > float(clip["start"])
            and float(item["start"]) < float(clip["end"])
        ]
        text = " ".join(item.get("text", "").strip() for item in overlapping).strip()

    if not text:
        raise RuntimeError(
            f"Short {index:02d} has no spoken transcript for English narration."
        )

    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = Path(f"output/voice_{index:02d}.wav")
    srt_path = Path(f"output/short_{index:02d}.srt")

    command = [
        "python", "-m", "piper",
        "--model", VOICE,
        "--data-dir", str(VOICE_DIR),
        "--output_file", str(audio_path),
        "--", text
    ]
    subprocess.run(command, check=True)

    entries = make_caption_entries(clip, transcript)
    if not entries:
        entries = [(0.0, float(clip["duration"]), text)]

    srt_lines = []
    for number, (begin, finish, caption) in enumerate(entries, start=1):
        srt_lines.extend([
            str(number),
            f"{srt_time(begin)} --> {srt_time(finish)}",
            caption,
            ""
        ])
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    return str(audio_path), str(srt_path)


if __name__ == "__main__":
    sample = {"start": 0, "end": 10, "duration": 10, "text": "This is a voice test."}
    audio, captions = create_narration(sample, 99)
    print(audio, captions)
