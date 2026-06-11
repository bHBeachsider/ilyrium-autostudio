#!/usr/bin/env python3
"""
prop_concepts.py - manage pro-forma prop CONCEPTS (Midjourney/AI/hand) for evaluation,
keeping them separate from the CC0 museum references, and bridge the shortlist into the
Astria refine op (producer.refine_shot_astria).

Workflow
  1. init     scaffold projects/<proj>/03_design/props/_concepts/<category>/ + a SCORECARD.csv
  2. (drop concept images into each category folder — e.g. Midjourney exports)
  3. scan     add a scorecard row for every new image (idempotent)
  4. (score each row in the CSV: 1-5 per axis, set provenance_flag, mark selected=y)
  5. shortlist  emit _concepts/refine_queue.json — one refine body per selected concept,
                ready for producer.refine_shot_astria once you set garment_image_url.

Concepts are NOT production assets. A shortlisted concept is a SEED: it feeds the refine
op as a garment/reference image to put the item on the character (identity lock + provenance
re-grounding happen there, not here).

USAGE
  python prop_concepts.py init --project satesh                 # default category set
  python prop_concepts.py init --project satesh --category belt
  python prop_concepts.py scan --project satesh                 # all categories
  python prop_concepts.py scan --project satesh --category sash
  python prop_concepts.py shortlist --project satesh            # selected=y rows
  python prop_concepts.py shortlist --project satesh --min-score 16
"""
from __future__ import annotations
import argparse, csv, json, os, sys

# Scorecard schema. Four 1-5 evaluation axes + a provenance flag + bookkeeping.
AXES = ["period_accuracy", "silhouette", "palette", "on_character_viability"]
COLS = ["category", "file", "source", "period_accuracy", "silhouette", "palette",
        "on_character_viability", "provenance_flag", "total", "selected", "notes"]

# Default categories for an India-themed wardrobe. `clothes` -> robe (jama/angarkha/sherwani).
DEFAULT_CATEGORIES = ["sash", "belt", "shoes", "robe", "turban_ornament", "dagger", "textile"]

# Per-category prompt fragment used when generating the refine body `text`.
CATEGORY_PROMPT = {
    "sash": "wearing an ornate patka sash at the waist",
    "belt": "wearing a jewelled waist belt / kamarband",
    "shoes": "wearing embroidered mojari / jutti footwear",
    "robe": "wearing a Mughal jama / angarkha robe",
    "turban_ornament": "wearing a turban with a sarpech / kalgi ornament",
    "dagger": "with a katar dagger at the waist",
    "textile": "in garments of this textile pattern",
}
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")


def _proj_root(project: str) -> str:
    from project_paths import resolve_project
    return resolve_project(project)


def _concepts_dir(project: str) -> str:
    return os.path.join(_proj_root(project), "03_design", "props", "_concepts")


def _cat_dir(project: str, category: str) -> str:
    return os.path.join(_concepts_dir(project), category)


def _scorecard_path(project: str, category: str) -> str:
    return os.path.join(_cat_dir(project, category), "SCORECARD.csv")


def _read_rows(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(path: str, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _total(row: dict) -> int:
    s = 0
    for a in AXES:
        try:
            s += int(float(row.get(a) or 0))
        except (TypeError, ValueError):
            pass
    return s


def cmd_init(project: str, categories: list[str]) -> None:
    root = _concepts_dir(project)
    os.makedirs(root, exist_ok=True)
    readme = os.path.join(root, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as f:
            f.write(_CONCEPTS_README)
    for c in categories:
        d = _cat_dir(project, c)
        os.makedirs(d, exist_ok=True)
        sc = _scorecard_path(project, c)
        if not os.path.exists(sc):
            _write_rows(sc, [])
        print(f"[init] {c}: {os.path.relpath(d, _proj_root(project))}/")
    print(f"\n_concepts ready under {os.path.relpath(root, _proj_root(project))}/ "
          f"({len(categories)} categories). Drop concept images in, then `scan`.")


def cmd_scan(project: str, categories: list[str]) -> None:
    total_new = 0
    for c in categories:
        d = _cat_dir(project, c)
        if not os.path.isdir(d):
            print(f"[scan] {c}: no folder — run init first"); continue
        sc = _scorecard_path(project, c)
        rows = _read_rows(sc)
        have = {r["file"] for r in rows}
        imgs = sorted(fn for fn in os.listdir(d) if fn.lower().endswith(IMG_EXT))
        new = 0
        for fn in imgs:
            if fn in have:
                continue
            # provenance heuristic: filename hints at a Midjourney export
            prov = "mj-derived" if any(t in fn.lower() for t in ("mj", "midjourney", "_oref", "_sref")) else "unknown"
            rows.append({"category": c, "file": fn, "source": "concept",
                         "period_accuracy": "", "silhouette": "", "palette": "",
                         "on_character_viability": "", "provenance_flag": prov,
                         "total": "", "selected": "", "notes": ""})
            new += 1
        if new:
            _write_rows(sc, rows)
        print(f"[scan] {c}: {new} new, {len(rows)} total")
        total_new += new
    print(f"\n{total_new} new concept(s) added across {len(categories)} categories.")


def _selected(row: dict, min_score: int | None) -> bool:
    sel = (row.get("selected") or "").strip().lower()
    if sel in ("y", "yes", "true", "1", "x"):
        return True
    if min_score is not None and _total(row) >= min_score:
        return True
    return False


def cmd_shortlist(project: str, categories: list[str], min_score: int | None,
                  model_family: str, num_images: int) -> None:
    queue = []
    for c in categories:
        sc = _scorecard_path(project, c)
        rows = _read_rows(sc)
        for r in rows:
            r["total"] = str(_total(r))            # refresh totals from the axes
        if rows:
            _write_rows(sc, rows)
        for r in rows:
            if not _selected(r, min_score):
                continue
            local = os.path.join(_cat_dir(project, c), r["file"])
            frag = CATEGORY_PROMPT.get(c, f"wearing {c}")
            queue.append({
                "op": "astria_refine",
                "category": c,
                "concept_file": r["file"],
                "_local_image": os.path.relpath(local, _proj_root(project)),
                "provenance_flag": r.get("provenance_flag", "unknown"),
                "score": _total(r),
                # ---- refine_shot_astria body (fill garment_image_url after hosting _local_image) ----
                "model_family": model_family,
                "garment_image_url": None,
                "controlnet": "reference",
                "denoising_strength": 0.6,
                "num_images": num_images,
                "text": f"satesh, {frag}, full-length, studio lighting, photorealistic",
            })
    out = os.path.join(_concepts_dir(project), "refine_queue.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"project": project, "count": len(queue), "items": queue}, f, indent=2)
    print(f"[shortlist] {len(queue)} selected concept(s) -> {os.path.relpath(out, _proj_root(project))}")
    if queue:
        print("  NOTE: each item needs garment_image_url set (host _local_image to a public URL) "
              "before posting to the Stage-4 astria_refine op.")
    for q in queue:
        print(f"   • {q['category']:16} {q['concept_file']:32} score={q['score']:>2} "
              f"prov={q['provenance_flag']}")


_CONCEPTS_README = """# _concepts — pro-forma prop concepts (evaluation staging)

These are PROVISIONAL prop concepts (Midjourney / AI / hand sketches) generated to be
**evaluated**, not shipped. They are kept separate from the CC0 museum references in
`../wardrobe_refs/` precisely because they do NOT share that clean public-domain provenance.

## Loop
1. `prop_concepts.py init` made these category folders + an empty `SCORECARD.csv` in each.
2. Drop concept images into the matching category folder (e.g. Midjourney exports into `sash/`).
3. `prop_concepts.py scan` adds a scorecard row per image.
4. Score each row in `SCORECARD.csv` — 1-5 on each axis:
   - **period_accuracy** — historically right for 19th-c Indian nobility? (judge against
     `../wardrobe_refs/`, NOT against the concept itself)
   - **silhouette** — shape/cut/proportion
   - **palette** — colour & material read
   - **on_character_viability** — will it sit believably on satesh?
   - **provenance_flag** — `clean` | `mj-derived` | `unknown` (anything that may ship must be
     re-grounded; mj-derived output carries Midjourney terms, not CC0)
   Set `selected` = `y` for keepers.
5. `prop_concepts.py shortlist` emits `refine_queue.json` — one `astria_refine` body per
   keeper. Host the concept image, set `garment_image_url`, and POST it to the Stage-4
   refine op to put the item on the character.

A shortlisted concept is a SEED, not a final asset.
"""


def main():
    ap = argparse.ArgumentParser(description="Manage pro-forma prop concepts for evaluation.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "scan", "shortlist"):
        p = sub.add_parser(name)
        p.add_argument("--project", default="satesh")
        p.add_argument("--category", help="single category (default: all)")
    sub.choices["shortlist"].add_argument("--min-score", type=int, dest="min_score",
                                          help="also select rows with total >= N")
    sub.choices["shortlist"].add_argument("--model-family", default="flux",
                                          choices=["flux", "sdxl"])
    sub.choices["shortlist"].add_argument("--num-images", type=int, default=4, dest="num_images")
    a = ap.parse_args()

    cats = [a.category] if a.category else DEFAULT_CATEGORIES
    if a.cmd == "init":
        cmd_init(a.project, cats)
    elif a.cmd == "scan":
        cmd_scan(a.project, cats)
    elif a.cmd == "shortlist":
        cmd_shortlist(a.project, cats, a.min_score, a.model_family, a.num_images)


if __name__ == "__main__":
    main()
