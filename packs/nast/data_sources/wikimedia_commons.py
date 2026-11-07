"""Wikimedia Commons high-resolution public-domain category harvester.

Recursively gathers full-resolution images from a Commons category tree,
filtering by minimum pixel dimension.

Run command:
    python -m packs.nast.data_sources.wikimedia_commons \\
        --category "Category:Works by Thomas Nast" \\
        --out packs/nast/data/hand/raw \\
        --depth 2 \\
        --min-px 1200
"""

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error
import time
from collections import deque

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "slm-foundry/1.0 (https://ilyrium.io; dataset research)"}


# ---------------------------------------------------------------------------
# Pure / offline helpers (tested without network)
# ---------------------------------------------------------------------------

def split_members(payload: dict) -> tuple[list[str], list[str]]:
    """Split categorymembers payload into (file_titles, subcat_titles).

    ns==6  -> file
    ns==14 -> subcategory
    """
    members = payload.get("query", {}).get("categorymembers", [])
    files = [m["title"] for m in members if m.get("ns") == 6]
    subcats = [m["title"] for m in members if m.get("ns") == 14]
    return files, subcats


def pick_files(payload: dict, min_px: int) -> list[dict]:
    """Extract image records from an imageinfo query response.

    Skips pages that have no ``imageinfo`` key.
    Keeps only pages where max(width, height) >= min_px.

    Returns a list of dicts with keys: title, url, width, height.
    """
    pages = payload.get("query", {}).get("pages", {})
    result = []
    for page in pages.values():
        infos = page.get("imageinfo")
        if not infos:
            continue
        info = infos[0]
        width = info.get("width", 0)
        height = info.get("height", 0)
        if max(width, height) >= min_px:
            result.append({
                "title": page["title"],
                "url": info["url"],
                "width": width,
                "height": height,
            })
    return result


# ---------------------------------------------------------------------------
# Network helpers (runtime only — not exercised during tests)
# ---------------------------------------------------------------------------

def _get(params: dict, _tries: int = 6) -> dict:
    """GET the Commons API with retry/backoff on 429/503, plus a polite delay."""
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(_tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            time.sleep(0.5)            # be polite to the Commons API
            return data
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < _tries - 1:
                time.sleep(2 * (2 ** attempt))   # 2,4,8,16,32s backoff
                continue
            raise


def list_category_files(category: str, depth: int = 2) -> list[str]:
    """BFS the category tree up to ``depth`` levels; return deduplicated file titles."""
    seen_files: set[str] = set()
    # Each queue entry: (category_title, remaining_depth)
    queue: deque[tuple[str, int]] = deque([(category, depth)])
    visited_cats: set[str] = set()

    while queue:
        cat, remaining = queue.popleft()
        if cat in visited_cats:
            continue
        visited_cats.add(cat)

        # Paginate through all members of this category
        params: dict = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cat,
            "cmlimit": 500,
            "format": "json",
        }
        while True:
            data = _get(params)
            files, subcats = split_members(data)
            seen_files.update(files)

            if remaining > 0:
                for sc in subcats:
                    if sc not in visited_cats:
                        queue.append((sc, remaining - 1))

            cont = data.get("continue", {}).get("cmcontinue")
            if cont:
                params["cmcontinue"] = cont
            else:
                break

    return list(seen_files)


def image_infos(titles: list[str]) -> list[dict]:
    """Fetch imageinfo for a list of file titles (batched 50 at a time).

    Returns combined [{title, url, width, height}] for all files,
    with min_px=0 so nothing is filtered out.
    """
    results: list[dict] = []
    batch_size = 50
    for i in range(0, len(titles), batch_size):
        batch = titles[i : i + batch_size]
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "imageinfo",
            "iiprop": "url|size",
            "format": "json",
        }
        data = _get(params)
        results.extend(pick_files(data, min_px=0))
    return results


def download(files: list[dict], out_dir: str, min_px: int = 1200) -> int:
    """Download full-resolution images to out_dir.

    Filters to max(width, height) >= min_px.
    Filename: strip "File:" prefix, replace spaces with underscores.
    Skips on error.
    Returns count of successfully downloaded files.
    """
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    failed = 0
    eligible = [f for f in files if max(f.get("width", 0), f.get("height", 0)) >= min_px]
    print(f"downloading {len(eligible)} of {len(files)} files (>= {min_px}px)...")
    for f in eligible:
        name = re.sub(r"^File:", "", f["title"]).replace(" ", "_")
        dest = os.path.join(out_dir, name)
        if os.path.exists(dest):          # resume-friendly: skip already downloaded
            count += 1
            continue
        ok = False
        for attempt in range(5):
            try:
                req = urllib.request.Request(f["url"], headers=UA)
                with urllib.request.urlopen(req, timeout=120) as resp:
                    body = resp.read()
                with open(dest, "wb") as fh:
                    fh.write(body)
                ok = True
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 503) and attempt < 4:
                    time.sleep(2 * (2 ** attempt))   # backoff 2,4,8,16s
                    continue
                break
            except Exception:
                time.sleep(1)
                continue
        if ok:
            count += 1
        else:
            failed += 1
            print(f"  FAILED: {name}")
        time.sleep(0.4)                    # polite pacing between image fetches
        if count % 25 == 0 and count:
            print(f"  progress: {count} downloaded, {failed} failed")
    print(f"download complete: {count} ok, {failed} failed")
    return count


def parse_search(payload: dict) -> list[str]:
    """File titles from a list=search response (pure/offline)."""
    return [h["title"] for h in payload.get("query", {}).get("search", [])]


def search_files(query: str, limit: int = 5000) -> list[str]:
    """All File-namespace titles matching a Commons full-text search (paged)."""
    titles: list[str] = []
    params = {"action": "query", "list": "search", "srsearch": query,
              "srnamespace": 6, "srlimit": 500, "format": "json"}
    while True:
        data = _get(params)
        titles.extend(parse_search(data))
        off = data.get("continue", {}).get("sroffset")
        if off is None or len(titles) >= limit:
            break
        params["sroffset"] = off
    return titles


def harvest_universe(out_dir: str, categories: list[str], query: str,
                     depth: int = 4, min_px: int = 768) -> int:
    """Comprehensive harvest: union of category trees + full-text file search, deduped."""
    titles: set[str] = set()
    for cat in categories:
        found = list_category_files(cat, depth=depth)
        print(f"  {cat}: {len(found)} files")
        titles.update(found)
    # NOTE: full-text file search (list=search "Thomas Nast") is intentionally NOT used.
    # It returned ~5000 files (capped) — mostly NOT by Nast, just any file MENTIONING him,
    # pulled from LOC/MET/DPLA/etc. The category tree is the authoritative corpus of his works.
    print(f"universe (categories only): {len(titles)} unique file titles")
    infos = image_infos(sorted(titles))
    return download(infos, out_dir, min_px=min_px)


def harvest(category: str, out_dir: str, depth: int = 2, min_px: int = 1200) -> int:
    """End-to-end harvest: list files -> fetch infos -> download.

    Returns count of downloaded images.
    """
    titles = list_category_files(category, depth=depth)
    infos = image_infos(titles)
    return download(infos, out_dir, min_px=min_px)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Harvest high-res public-domain images from a Wikimedia Commons category tree."
    )
    parser.add_argument(
        "--category",
        default="Category:Works by Thomas Nast",
        help="Root Commons category (default: 'Category:Works by Thomas Nast')",
    )
    parser.add_argument(
        "--out",
        default="packs/nast/data/hand/raw",
        help="Output directory for downloaded images",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Category tree recursion depth (default: 2)",
    )
    parser.add_argument(
        "--min-px",
        type=int,
        default=1200,
        dest="min_px",
        help="Minimum pixel dimension to keep (default: 1200)",
    )
    parser.add_argument(
        "--comprehensive", action="store_true",
        help="Harvest the ENTIRE Nast universe: union all Nast categories + full-text file search.",
    )
    parser.add_argument(
        "--query", default="Thomas Nast",
        help="Full-text search query used in --comprehensive mode (default: 'Thomas Nast')",
    )
    args = parser.parse_args()

    if args.comprehensive:
        n = harvest_universe(
            args.out,
            categories=["Category:Thomas Nast", "Category:Works by Thomas Nast"],
            query=args.query, depth=args.depth, min_px=args.min_px,
        )
    else:
        n = harvest(args.category, args.out, depth=args.depth, min_px=args.min_px)
    print(f"harvested {n} images >= {args.min_px}px -> {args.out}")


if __name__ == "__main__":
    main()
