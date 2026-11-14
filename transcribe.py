
from faster_whisper import WhisperModel
from pathlib import Path
import json

def transcribe_video(video_path):
    print("Loading speech recognition model...")

    model = WhisperModel(
        "tiny",
        device="cpu",
        compute_type="int8"
    )

    segments, info = model.transcribe(
        str(video_path),
        beam_size=3,
        vad_filter=True
    )

    transcript = []

    for segment in segments:
        transcript.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip()
        })

    return transcript


if __name__ == "__main__":
    video = Path("input.mp4")

    if not video.exists():
        raise FileNotFoundError("input.mp4 not found")

    result = transcribe_video(video)

    Path("transcript.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Transcription complete: {len(result)} segments")
