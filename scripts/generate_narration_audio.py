#!/usr/bin/env python3
"""Synthesize chapter narration with free Edge TTS and create timed English subtitle cues."""
import argparse
import asyncio
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def split_cues(text, max_words=13):
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    cues = []
    for sentence in sentences:
        words = sentence.split()
        for start in range(0, len(words), max_words):
            chunk = " ".join(words[start:start + max_words]).strip()
            if chunk:
                cues.append(chunk)
    return cues


def probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise ValueError("TTS output has invalid duration.")
    return duration


def srt_timestamp(seconds):
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


async def synthesize(plan, output_audio, output_srt, voice, rate):
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("edge-tts is not installed; install the free edge-tts package.") from exc
    chapters = plan.get("chapters", [])
    if not chapters:
        raise ValueError("Plan has no chapters.")
    root = Path(output_audio).resolve().parent
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="koroush-tts-") as temp_dir:
        temp = Path(temp_dir)
        audio_files, cue_groups = [], []
        for index, chapter in enumerate(chapters, 1):
            narration = re.sub(r"\s+", " ", str(chapter.get("narration", ""))).strip()
            if not narration:
                raise ValueError(f"Chapter {index} has empty narration.")
            target = temp / f"chapter_{index:03d}.mp3"
            last_error = None
            for attempt in range(3):
                try:
                    await edge_tts.Communicate(narration, voice, rate=rate).save(str(target))
                    if target.is_file() and target.stat().st_size > 1000:
                        last_error = None
                        break
                    raise RuntimeError("TTS returned an empty audio file.")
                except Exception as exc:
                    last_error = exc
                    await asyncio.sleep(1 + attempt * 2)
            if last_error:
                fallback = temp / f"chapter_{index:03d}.wav"
                if not shutil.which("espeak-ng"):
                    raise RuntimeError(f"TTS failed on chapter {index}; no offline espeak-ng fallback is installed.") from last_error
                subprocess.run(["espeak-ng", "-v", "en-us", "-s", "150", "-w", str(fallback), narration], check=True)
                target = fallback
            duration = probe_duration(target)
            audio_files.append(target)
            cue_groups.append((split_cues(narration), duration))

        concat_file = temp / "concat.txt"
        concat_file.write_text("".join(f"file '{path.as_posix()}'\n" for path in audio_files), encoding="utf-8")
        output_audio = Path(output_audio).resolve()
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
            "-safe", "0", "-i", str(concat_file), "-c:a", "libmp3lame", "-q:a", "3",
            str(output_audio)
        ], check=True)

        rows, cursor, cue_index = [], 0.0, 1
        for cues, duration in cue_groups:
            weights = [max(1, len(cue.split())) for cue in cues]
            total = sum(weights)
            local = 0.0
            for cue, weight in zip(cues, weights):
                start = cursor + duration * local / total
                local += weight
                end = cursor + duration * local / total
                rows.append(f"{cue_index}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{cue}")
                cue_index += 1
            cursor += duration
        Path(output_srt).resolve().write_text("\n\n".join(rows) + "\n", encoding="utf-8")
    return {"audio": str(output_audio), "english_srt": str(Path(output_srt).resolve()),
            "chapters": len(chapters), "subtitle_cues": cue_index - 1, "duration_seconds": round(cursor, 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--audio", default="longform-output/narration.mp3")
    parser.add_argument("--srt", default="longform-output/narration.en.srt")
    parser.add_argument("--voice", default="en-US-AriaNeural")
    parser.add_argument("--rate", default="+0%")
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    result = asyncio.run(synthesize(plan, args.audio, args.srt, args.voice, args.rate))
    print("NARRATION_AUDIO_READY " + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
