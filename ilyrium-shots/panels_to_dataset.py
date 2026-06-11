#!/usr/bin/env python3
"""
panels_to_dataset.py — Broderick panel art -> captioned LoRA training dataset.

Joins each source panel image to its parsed scene card(s) (02_script/scenes.json),
the strip's extrapolated style kernel (style_kernel.json), and the master-kernel
style family, then emits a training-ready dataset:

    <out>/images/<strip>__<NN>.<ext>      normalized image copies
    <out>/images/<strip>__<NN>.txt        per-image caption (kohya / ai-toolkit)
    <out>/metadata.jsonl                  {"file_name","caption"} (HF imagefolder)
    <out>/manifest.jsonl                  full provenance per image: strip,
                                          style_family, color_mode, wxh, sha256,
                                          scene_numbers, excluded(+reason)
    <out>/DATASET_CARD.md                 counts, exclusions, caption conventions

Caption shape (natural language, Flux/T5-friendly; also fine for SDXL):
    "<trigger> style, <kernel-derived style line>. <scene visual content>."

Panels->cards mapping: 1:1 by order when counts match; when one image holds
multiple drawn panels (cards > images, evenly divisible) cards are chunked in
order; otherwise content text falls back to the strip treatment's logline.

Exclusions: strips listed in EXCLUDE (rights-encumbered vintage stock art) are
manifest-logged but not copied into images/.

Stdlib only (PNG/JPEG dimensions parsed by hand).

RUN (from repo root, Windows or POSIX):
    python ilyrium-shots/panels_to_dataset.py \
        --client projects/broderick --out projects/broderick/_training/dataset_v0 \
        --trigger brdrck
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import struct
import sys

EXCLUDE = {
    "broderick_karate_kicks": "vintage stock-art collage with residual watermarks; rights unclear",
}
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def image_size(path):
    """PNG / JPEG dimensions, stdlib only. Returns (w, h) or (None, None)."""
    with open(path, "rb") as f:
        head = f.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", head[16:24])
            return w, h
        if head[:2] == b"\xff\xd8":  # JPEG: scan for SOFn
            f.seek(2)
            while True:
                seg = f.read(4)
                if len(seg) < 4:
                    return None, None
                marker, size = seg[0:2], struct.unpack(">H", seg[2:4])[0]
                if marker[0] != 0xFF:
                    return None, None
                if 0xC0 <= marker[1] <= 0xCF and marker[1] not in (0xC4, 0xC8, 0xCC):
                    data = f.read(5)
                    h, w = struct.unpack(">HH", data[1:5])
                    return w, h
                f.seek(size - 2, 1)
    return None, None


def style_line(kernel):
    """Compress the per-strip kernel look into a caption-friendly style line."""
    look = kernel.get("look", "")
    # first two sentences / clauses, stripped of meta commentary
    parts = re.split(r"(?<=[.;])\s+", look)
    line = " ".join(parts[:2]).strip().rstrip(".;")
    return re.sub(r"\s+", " ", line)


_GRAY_WORDS = ("grayscale", "greyscale", "monochrome", "b/w", "b&w",
               "black and white", "black-and-white", "pure black", "gray wash",
               "grey wash")


def color_mode(kernel):
    look = kernel.get("look", "").lower()
    if any(w in look for w in _GRAY_WORDS) and "full color" not in look:
        return "grayscale"
    if "color" in look:
        return "color"
    return "unknown"


def content_text(cards):
    """Scene-card content -> one caption clause."""
    bits = []
    for c in cards:
        vp = (c.get("visual_prompt") or "").strip()
        if vp:
            bits.append(vp.rstrip("."))
    return " | ".join(bits) if bits else ""


def map_cards(images, cards):
    """Return list[ list[card] ] aligned to images (see module doc)."""
    n_i, n_c = len(images), len(cards)
    if n_i == n_c:
        return [[c] for c in cards]
    if n_c > n_i and n_c % n_i == 0:
        k = n_c // n_i
        return [cards[i * k:(i + 1) * k] for i in range(n_i)]
    # mismatch: pad/truncate 1:1, leftover cards appended to the last image
    out = [[c] for c in cards[:n_i]]
    while len(out) < n_i:
        out.append([])
    if n_c > n_i:
        out[-1].extend(cards[n_i:])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", default=os.path.join("projects", "broderick"),
                    help="client folder containing broderick_* project dirs")
    ap.add_argument("--out", default=os.path.join("projects", "broderick",
                                                  "_training", "dataset_v0"))
    ap.add_argument("--trigger", default="brdrck",
                    help="LoRA trigger token prefixed to every caption")
    ap.add_argument("--include-excluded", action="store_true",
                    help="also copy rights-flagged strips into images/")
    a = ap.parse_args()

    img_dir = os.path.join(a.out, "images")
    os.makedirs(img_dir, exist_ok=True)

    manifest, metadata = [], []
    n_imgs = n_excluded = 0
    strips = sorted(d for d in glob.glob(os.path.join(a.client, "broderick_*"))
                    if os.path.isdir(d))
    if not strips:
        sys.exit(f"no broderick_* projects under {a.client}")

    for proj in strips:
        slug = os.path.basename(proj)
        panels = [p for p in sorted(glob.glob(
            os.path.join(proj, "01_development", "bible", "panels", "*")))
            if os.path.splitext(p)[1].lower() in IMAGE_EXTS]
        if not panels:
            continue
        kernel = json.load(open(os.path.join(proj, "style_kernel.json"),
                                encoding="utf-8"))
        cards = json.load(open(os.path.join(proj, "02_script", "scenes.json"),
                               encoding="utf-8"))
        sline = style_line(kernel)
        cmode = color_mode(kernel)
        card_groups = map_cards(panels, cards)
        excluded = slug in EXCLUDE and not a.include_excluded

        for i, (src, group) in enumerate(zip(panels, card_groups), 1):
            ext = os.path.splitext(src)[1].lower().replace(".jpeg", ".jpg")
            name = f"{slug}__{i:02d}{ext}"
            w, h = image_size(src)
            content = content_text(group)
            caption = f"{a.trigger} style, {sline}."
            if content:
                caption += f" {content}."
            caption = re.sub(r"\s+", " ", caption).strip()
            row = {
                "file_name": f"images/{name}", "caption": caption,
                "strip": slug, "color_mode": cmode,
                "width": w, "height": h, "sha256": sha256(src),
                "source_panel": os.path.basename(src),
                "scene_numbers": [c.get("scene_number") for c in group],
                "excluded": bool(excluded),
                "exclude_reason": EXCLUDE.get(slug, "") if excluded else "",
            }
            manifest.append(row)
            if excluded:
                n_excluded += 1
                continue
            shutil.copy2(src, os.path.join(img_dir, name))
            with open(os.path.join(img_dir, os.path.splitext(name)[0] + ".txt"),
                      "w", encoding="utf-8") as f:
                f.write(caption + "\n")
            metadata.append({"file_name": f"images/{name}", "caption": caption})
            n_imgs += 1

    with open(os.path.join(a.out, "manifest.jsonl"), "w", encoding="utf-8") as f:
        for r in manifest:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(a.out, "metadata.jsonl"), "w", encoding="utf-8") as f:
        for r in metadata:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    gray = sum(1 for r in manifest if not r["excluded"] and r["color_mode"] == "grayscale")
    color = sum(1 for r in manifest if not r["excluded"] and r["color_mode"] == "color")
    with open(os.path.join(a.out, "DATASET_CARD.md"), "w", encoding="utf-8") as f:
        f.write(f"""# Broderick panel LoRA dataset v0

Generated by ilyrium-shots/panels_to_dataset.py from {len(strips)} strip projects.

| | |
|---|---|
| training images | {n_imgs} |
| grayscale / color | {gray} / {color} |
| excluded (rights) | {n_excluded} ({', '.join(EXCLUDE)}) |
| trigger token | `{a.trigger}` |

Caption convention: `<trigger> style, <kernel style line>. <scene-card visual content>.`
Natural-language captions — suitable for Flux (T5) and usable for SDXL/Wan.
Images contain original hand lettering; captions note dialogue presence implicitly
via scene content. Crop-text variants can be derived later if lettering pollutes
the style.

Files: images/ (+ per-image .txt sidecars, kohya/ai-toolkit convention),
metadata.jsonl (HF imagefolder), manifest.jsonl (full provenance incl. excluded rows).
Source of truth remains projects/broderick/<strip>/ — regenerate, don't hand-edit.
""")
    print(f"dataset: {n_imgs} images ({gray} grayscale, {color} color), "
          f"{n_excluded} excluded, {len(strips)} strips -> {a.out}")


if __name__ == "__main__":
    main()
