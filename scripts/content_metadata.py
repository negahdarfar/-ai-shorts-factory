"""Extract lightweight, reviewable metadata for Shorts hooks."""
import re


def extract_hook(script: str, max_length: int = 300) -> str:
    text = re.sub(r"\s+", " ", str(script or "").strip())
    if not text:
        return ""
    match = re.search(r"(.+?[.!?])(?:\s|$)", text)
    hook = match.group(1).strip() if match else text
    return hook[:max_length].strip()


def classify_hook(hook: str) -> str:
    text = re.sub(r"\s+", " ", str(hook or "").strip()).casefold()
    if not text:
        return "unknown"
    if "?" in text or re.match(r"^(why|how|what|when|where|who|can|could|did|does|is|are)\b", text):
        return "question"
    if re.match(r"^(imagine|picture this|what if)\b", text):
        return "scenario"
    if re.match(r"^(most people think|you might think|everyone thinks|actually|but)\b", text):
        return "contrarian"
    if re.match(r"^(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", text):
        return "number_or_fact"
    if re.match(r"^(scientists|researchers|here is|here's|this is|the truth is)\b", text):
        return "direct_fact"
    return "curiosity"
