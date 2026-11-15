from faster_whisper import WhisperModel
from pathlib import Path
import json


def transcribe_video(video_path):
    print("Loading speech recognition model...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")

    # Translate source speech to English so the English Piper voice
    # and English captions remain consistent, even for non-English sources.
    segments, info = model.transcribe(
        str(video_path),
        beam_size=3,
        vad_filter=True,
        task="translate"
    )

    transcript = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            transcript.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text
            })

    print("Detected source language:", getattr(info, "language", "unknown"))
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
    print(f"English translation complete: {len(result)} segments")
