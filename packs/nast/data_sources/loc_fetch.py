"""Library of Congress JSON API: search Nast works + metadata (image download in Phase 2)."""
import json, time, urllib.parse, urllib.request, re, pathlib

BASE = "https://www.loc.gov/search/"


def parse_results(payload: dict) -> list[dict]:
    out = []
    for r in payload.get("results", []):
        urls = r.get("image_url") or []
        if not urls:
            continue
        largest = urls[-1]
        if largest.startswith("//"):
            largest = "https:" + largest
        out.append({"id": r.get("id", ""), "title": r.get("title", ""),
                    "date": r.get("date", ""), "image_url": largest})
    return out


def search_loc(query: str = "Thomas Nast", pages: int = 1, per_page: int = 100) -> list[dict]:
    items = []
    for page in range(1, pages + 1):
        qs = urllib.parse.urlencode({"q": query, "fo": "json", "c": per_page, "sp": page})
        req = urllib.request.Request(f"{BASE}?{qs}", headers={"User-Agent": "slm-foundry/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            items.extend(parse_results(json.loads(resp.read())))
        time.sleep(1)
    return items


def safe_filename(item: dict, idx: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", item.get("title", "").lower()).strip("-")[:40] or "nast"
    return f"{idx:03d}_{slug}.jpg"


def download_images(items: list[dict], out_dir: str) -> int:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for i, it in enumerate(items):
        if not it.get("image_url"):
            continue
        dest = out / safe_filename(it, i)
        try:
            req = urllib.request.Request(it["image_url"], headers={"User-Agent": "slm-foundry/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                f.write(r.read())
            n += 1
        except Exception as e:
            print(f"  skip {dest.name}: {e}")
    return n


if __name__ == "__main__":
    found = search_loc("Thomas Nast", pages=1)
    print(f"{len(found)} items with images")
    for it in found[:5]:
        print(it["date"], "-", it["title"])
