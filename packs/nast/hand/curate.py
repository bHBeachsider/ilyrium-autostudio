"""Curate the harvested Nast scans for style-LoRA training.

- Drops non-images and filename-flagged non-cartoons (portraits, signatures, maps, studies).
- Copies survivors raw/ -> train/.
- Builds a contact-sheet JPEG (thumbnail grid) for visual review.

  python packs/nast/hand/curate.py --raw packs/nast/data/hand/raw --out packs/nast/data/hand/train
"""
import argparse, re, shutil
from pathlib import Path
from PIL import Image

IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
# filename patterns that indicate NOT a wood-engraving political cartoon
CULL = re.compile(r"portrait|signature|self-portrait|nude|study|_map_|railroad_map|"
                  r"_NPG|_NGA|_MET_DP8601|panorama", re.I)


def curate(raw: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    kept, dropped = [], []
    for f in sorted(raw.iterdir()):
        if f.suffix.lower() not in IMG_EXT:
            dropped.append((f.name, "not-image")); continue
        if CULL.search(f.name):
            dropped.append((f.name, "filename-cull")); continue
        try:
            with Image.open(f) as im:
                w, h = im.size
            ar = max(w, h) / min(w, h)
            if ar > 3.0:                       # drop extreme panoramas/strips
                dropped.append((f.name, f"aspect {ar:.1f}")); continue
        except Exception as e:
            dropped.append((f.name, f"unreadable {e}")); continue
        shutil.copy2(f, out / f.name)
        kept.append(f.name)
    return kept, dropped


def contact_sheet(folder: Path, sheet_path: Path, thumb=150, cols=14):
    imgs = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in IMG_EXT]
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb, rows * thumb), "white")
    for i, p in enumerate(imgs):
        try:
            with Image.open(p) as im:
                im = im.convert("RGB"); im.thumbnail((thumb, thumb))
                x, y = (i % cols) * thumb, (i // cols) * thumb
                sheet.paste(im, (x + (thumb - im.width) // 2, y + (thumb - im.height) // 2))
        except Exception:
            pass
    sheet.save(sheet_path, quality=80)
    return len(imgs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="packs/nast/data/hand/raw")
    ap.add_argument("--out", default="packs/nast/data/hand/train")
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    kept, dropped = curate(raw, out)
    sheet = out.parent / "contact_sheet.jpg"
    n = contact_sheet(out, sheet)
    print(f"kept {len(kept)}, dropped {len(dropped)}  -> {out}")
    print(f"contact sheet ({n} imgs) -> {sheet}")
    print("dropped reasons:", {r: sum(1 for _, x in dropped if x == r) for r in set(x for _, x in dropped)})


if __name__ == "__main__":
    main()
