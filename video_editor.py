import subprocess
from pathlib import Path


def create_short(source, start, duration, output, voice, subtitles):
    source = str(source)
    output = str(output)
    voice = str(voice)
    subtitles = str(subtitles)

    # Source audio is retained quietly under the English narration.
    # Captions are burned into the vertical video for mobile viewing.
    subtitle_filter = (
        f"subtitles={subtitles}:"
        "force_style='FontName=DejaVu Sans,FontSize=16,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=150'"
    )

    command = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", source,
        "-i", voice,
        "-t", str(duration),
        "-filter_complex",
        (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,"
            + subtitle_filter
            + "[v];"
            "[0:a]volume=0.18[bg];"
            "[1:a]volume=1.0[vo];"
            "[bg][vo]amix=inputs=2:duration=first:dropout_transition=2[a]"
        ),
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        output
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    raise SystemExit(
        "Run main.py to create Shorts with narration and captions."
    )
