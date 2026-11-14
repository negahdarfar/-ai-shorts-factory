
import json
import re
from pathlib import Path

HOOK_WORDS = [
    "secret", "shocking", "amazing", "never",
    "impossible", "truth", "mistake", "discovered",
    "incredible", "surprising", "dangerous",
    "why", "how", "finally", "unexpected"
]

def score_clip(text):
    lower = text.lower()
    score = 0

    for word in HOOK_WORDS:
        if word in lower:
            score += 3

    if "?" in text:
        score += 3

    if "!" in text:
        score += 2

    if re.search(r"\d+", text):
        score += 2

    if 35 <= len(text.split()) <= 120:
        score += 3

    return score


def select_clips(transcript, count=4):
    candidates = []
    items = transcript

    for i in range(len(items)):
        start = items[i]["start"]
        end = start
        texts = []

        for j in range(i, len(items)):
            if items[j]["end"] - start > 55:
                break

            end = items[j]["end"]
            texts.append(items[j]["text"])

            duration = end - start

            if duration >= 30:
                full_text = " ".join(texts)

                candidates.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "duration": round(duration, 2),
                    "text": full_text,
                    "score": score_clip(full_text)
                })

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    selected = []

    for candidate in candidates:
        overlaps = any(
            not (
                candidate["end"] <= clip["start"]
                or candidate["start"] >= clip["end"]
            )
            for clip in selected
        )

        if not overlaps:
            selected.append(candidate)

        if len(selected) == count:
            break

    return selected


if __name__ == "__main__":
    source = Path("transcript.json")

    if not source.exists():
        raise FileNotFoundError("transcript.json not found")

    transcript = json.loads(
        source.read_text(encoding="utf-8")
    )

    result = select_clips(transcript)

    Path("best_clips.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Selected {len(result)} candidate clips.")
