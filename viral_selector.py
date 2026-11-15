import re

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
        if re.search(r"\b" + re.escape(word) + r"\b", lower):
            score += 3
    if "?" in text:
        score += 3
    if "!" in text:
        score += 2
    if re.search(r"\d+", text):
        score += 2
    words = len(text.split())
    if 20 <= words <= 100:
        score += 3
    return score


def _build_candidates(transcript, min_duration, max_duration):
    items = sorted(
        (
            {
                "start": float(item["start"]),
                "end": float(item["end"]),
                "text": str(item.get("text", "")).strip()
            }
            for item in transcript
            if str(item.get("text", "")).strip()
            and float(item["end"]) > float(item["start"])
        ),
        key=lambda item: item["start"]
    )

    candidates = []
    for i, first in enumerate(items):
        start = first["start"]
        texts = []
        last_end = start

        for item in items[i:]:
            if item["start"] - start > max_duration:
                break
            if item["start"] > last_end + 8:
                # Avoid joining widely separated speech into one narration.
                if last_end - start >= min_duration:
                    break
            if item["end"] - start > max_duration:
                break

            texts.append(item["text"])
            last_end = max(last_end, item["end"])
            duration = last_end - start

            if min_duration <= duration <= max_duration:
                full_text = " ".join(texts).strip()
                candidates.append({
                    "start": round(start, 2),
                    "end": round(last_end, 2),
                    "duration": round(duration, 2),
                    "text": full_text,
                    "score": score_clip(full_text)
                })

    # Remove exact duplicates while preserving the best score.
    unique = {}
    for candidate in candidates:
        key = (candidate["start"], candidate["end"])
        if key not in unique or candidate["score"] > unique[key]["score"]:
            unique[key] = candidate
    return list(unique.values())


def _choose_non_overlapping(candidates, count):
    candidates = sorted(
        candidates,
        key=lambda item: (
            item["score"],
            len(item["text"].split()),
            item["duration"]
        ),
        reverse=True
    )
    selected = []
    for candidate in candidates:
        overlaps = any(
            candidate["start"] < chosen["end"]
            and candidate["end"] > chosen["start"]
            for chosen in selected
        )
        if not overlaps:
            selected.append(candidate)
        if len(selected) == count:
            break
    return sorted(selected, key=lambda item: item["start"])


def select_clips(transcript, count=4):
    # Prefer useful 20-40 second spoken segments. If the source has
    # sparse speech, progressively relax the minimum duration rather
    # than failing immediately.
    for minimum in (20, 15, 10, 6):
        candidates = _build_candidates(
            transcript,
            min_duration=minimum,
            max_duration=40
        )
        selected = _choose_non_overlapping(candidates, count)
        if len(selected) == count:
            print(
                f"Selected {count} transcript clips "
                f"with minimum duration {minimum}s."
            )
            return selected

    print("Not enough non-overlapping transcript segments for four Shorts.")
    return []
