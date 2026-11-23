#!/usr/bin/env python3
"""Convert a validated UTF-8 SRT file to a standalone WebVTT sidecar."""
import argparse
import re
from pathlib import Path

TIMING = re.compile(r"^(\d{2,}:\d{2}:\d{2}),(\d{3}) --> (\d{2,}:\d{2}:\d{2}),(\d{3})$")


def convert_srt_to_vtt(source: Path, target: Path) -> int:
    raw = source.read_text(encoding="utf-8-sig").strip()
    blocks = re.split(r"\n\s*\n", raw)
    rendered = []
    previous_end = -1
    for block_number, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if len(lines) < 3 or not lines[0].strip().isdigit():
            raise ValueError(f"Malformed SRT cue {block_number}.")
        match = TIMING.fullmatch(lines[1].strip())
        if not match:
            raise ValueError(f"Malformed SRT timestamp in cue {block_number}.")
        start = f"{match.group(1)}.{match.group(2)}"
        end = f"{match.group(3)}.{match.group(4)}"
        def milliseconds(clock: str) -> int:
            clock_part, fraction_part = clock.split(".", 1)
            hours, minutes, seconds = (int(part) for part in clock_part.split(":"))
            if minutes > 59 or seconds > 59:
                raise ValueError(f"Invalid minute/second value in cue {block_number}.")
            fraction = int(fraction_part)
            return ((hours * 60 + minutes) * 60 + seconds) * 1000 + fraction
        start_ms = milliseconds(start)
        end_ms = milliseconds(end)
        if end_ms <= start_ms:
            raise ValueError(f"Subtitle cue {block_number} has a non-positive duration.")
        if start_ms < previous_end:
            raise ValueError(f"Subtitle cue {block_number} overlaps the previous cue.")
        previous_end = end_ms
        text = [line.rstrip() for line in lines[2:] if line.strip()]
        if not text:
            raise ValueError(f"Empty subtitle text in cue {block_number}.")
        rendered.append(f"{start} --> {end}\n" + "\n".join(text))
    if not rendered:
        raise ValueError("No subtitle cues found.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("WEBVTT\n\n" + "\n\n".join(rendered) + "\n", encoding="utf-8")
    return len(rendered)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    count = convert_srt_to_vtt(args.input, args.output)
    print(f"WEBVTT_SIDECAR_WRITTEN cues={count} path={args.output}")


if __name__ == "__main__":
    main()
