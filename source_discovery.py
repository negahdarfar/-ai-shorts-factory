
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"

SEARCH_TERMS = [
    "space astronomy video",
    "underwater ocean video",
    "wildlife nature video",
    "futuristic city video",
    "earth landscape video",
    "science technology video",
]

USER_AGENT = "ViralNovaLabsShortsFactory/1.0 (automated media discovery)"


def api_request(params):
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )

    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def allowed_license(value):
    text = str(value or "").lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()

    if any(x in text for x in ["noncommercial", "non commercial", " nc", " no derivatives", " nd"]):
        return False

    if "public domain" in text or "cc0" in text:
        return True

    if re.search(r"\bcc by sa\b", text):
        return True

    if re.search(r"\bcc by\b", text):
        return True

    return False


def search_videos(term):
    data = api_request({
        "action": "query",
        "generator": "search",
        "gsrsearch": "filetype:video " + term,
        "gsrnamespace": 6,
        "gsrlimit": 30,
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

        metadata = info.get("extmetadata", {})

        def get_meta(key):
            return metadata.get(key, {}).get("value", "")

        license_name = get_meta("LicenseShortName")
        license_url = get_meta("LicenseUrl")

        if not allowed_license(license_name):
            continue

        if not info.get("url"):
            continue

        results.append({
            "title": page.get("title", ""),
            "download_url": info["url"],
            "source_page": "https://commons.wikimedia.org/wiki/"
                           + urllib.parse.quote(page.get("title", "").replace(" ", "_")),
            "mime": mime,
            "size": info.get("size", 0),
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
            for item in search_videos(term):
                found[item["download_url"]] = item
        except Exception as error:
            print("Search warning:", error)

    results = sorted(
        found.values(),
        key=lambda item: item["size"],
        reverse=True
    )

    Path("source_candidates.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    if not results:
        raise RuntimeError("No eligible videos found.")

    print("Eligible video candidates:", len(results))
    return results


if __name__ == "__main__":
    discover_sources()
