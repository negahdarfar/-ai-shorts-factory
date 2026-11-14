
import json
import re
import html
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"

SEARCH_TERMS = [
    "space",
    "astronomy",
    "underwater ocean",
    "wildlife nature",
    "futuristic city",
    "earth landscape",
    "science technology",
    "mountains waterfall",
    "animals ocean",
    "documentary nature",
]

MIN_SIZE = 1 * 1024 * 1024
MAX_SIZE = 500 * 1024 * 1024
MIN_DURATION = 120

USER_AGENT = (
    "ViralNovaLabsShortsFactory/1.3 "
    "(https://github.com/negahdarfar/-ai-shorts-factory)"
)


def api_request(params):
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )

    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def allowed_license(value):
    text = clean_text(value).lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()

    if any(term in text for term in [
        "noncommercial",
        "non commercial",
        "no derivatives",
        "no derivative",
        "cc nc",
        "cc nd",
    ]):
        return False

    if "public domain" in text or "cc0" in text:
        return True

    if re.search(r"\bcc\s*by\s*sa\b", text):
        return True

    if re.search(r"\bcc\s*by\b", text):
        return True

    return False


def parse_duration(value):
    value = clean_text(value).lower()

    if not value:
        return None

    try:
        if re.fullmatch(r"\d+(\.\d+)?", value):
            return float(value)

        if ":" in value:
            parts = [float(x) for x in value.split(":")]
            seconds = 0

            for part in parts:
                seconds = seconds * 60 + part

            return seconds

        total = 0
        matches = re.findall(
            r"(\d+(?:\.\d+)?)\s*(h|hr|hour|hours|m|min|minute|minutes|s|sec|second|seconds)",
            value
        )

        if matches:
            for number, unit in matches:
                number = float(number)

                if unit.startswith("h"):
                    total += number * 3600
                elif unit.startswith("m"):
                    total += number * 60
                else:
                    total += number

            return total

    except (ValueError, TypeError):
        pass

    return None


def search_videos(term):
    data = api_request({
        "action": "query",
        "generator": "search",
        "gsrsearch": term,
        "gsrnamespace": 6,
        "gsrlimit": 50,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata"
    })

    pages = data.get("query", {}).get("pages", {})
    results = []

    for page in pages.values():
        info_list = page.get("imageinfo", [])

        if not info_list:
            continue

        info = info_list[0]
        mime = info.get("mime", "")

        if not mime.startswith("video/"):
            continue

        size = int(info.get("size", 0) or 0)

        if size < MIN_SIZE or size > MAX_SIZE:
            continue

        metadata = info.get("extmetadata", {})

        def get_meta(key):
            return clean_text(
                metadata.get(key, {}).get("value", "")
            )

        license_name = get_meta("LicenseShortName")
        license_url = get_meta("LicenseUrl")

        if not allowed_license(license_name):
            continue

        duration = parse_duration(
            get_meta("Length") or get_meta("Duration")
        )

        if duration is None or duration < MIN_DURATION:
            continue

        url = info.get("url", "")

        if not url.startswith("https://upload.wikimedia.org/"):
            continue

        title = page.get("title", "")

        results.append({
            "title": title,
            "download_url": url,
            "source_page": (
                "https://commons.wikimedia.org/wiki/"
                + urllib.parse.quote(title.replace(" ", "_"))
            ),
            "mime": mime,
            "size": size,
            "duration": duration,
            "license": license_name,
            "license_url": license_url,
            "artist": get_meta("Artist"),
            "credit": get_meta("Credit"),
            "description": get_meta("ImageDescription")
        })

    return results


def discover_sources():
    found = {}

    for term in SEARCH_TERMS:
        print("Searching:", term)

        try:
            videos = search_videos(term)

            for item in videos:
                found[item["download_url"]] = item

            print("Eligible results:", len(videos))

        except Exception as error:
            print("Search warning:", error)

    results = sorted(
        found.values(),
        key=lambda item: item["size"]
    )

    Path("source_candidates.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("Total eligible videos:", len(results))

    if not results:
        raise RuntimeError(
            "No eligible Wikimedia videos found. "
            "Try again later or expand search terms."
        )

    return results


if __name__ == "__main__":
    discover_sources()
