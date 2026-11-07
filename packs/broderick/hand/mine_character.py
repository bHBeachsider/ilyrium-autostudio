#!/usr/bin/env python3
"""mine_character.py — build the Broderick avatar character set for a character-consistency LoRA.

For each panel, Qwen3-VL (OpenRouter) detects the recurring author-avatar (heavyset, bald, full
gray beard, thick black rectangular glasses), returns a bounding box + a short pose, and we crop
him out. Output = clean isolated character crops + SHORT captions (`brdmc, <pose>`) — short on
purpose, so the `brdmc` trigger actually binds the identity (the long-caption mistake that made
`brdrck` inert).

Usage: python mine_character.py --src <dataset_v0 dir> [--out <char set dir>] [--limit N] [--review]
Env: OPENROUTER_API_KEY (in PermitHub/.env fallback). BRODERICK_VISION overrides model.
"""
import argparse, base64, json, os, re, time, urllib.request, urllib.error
from pathlib import Path
from PIL import Image

MODEL = os.environ.get("BRODERICK_VISION", "qwen/qwen3-vl-32b-instruct")
HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "data" / "char" / "brdmc" / "train"

PROMPT = """This is a single comic panel by the cartoonist Broderick. His recurring AUTHOR-AVATAR is a \
HEAVYSET BALD man with a FULL GRAY/WHITE BEARD and THICK BLACK rectangular glasses (often a gray \
work shirt).

Decide if THAT specific man is present AND a clear, prominent figure in this panel (not a tiny \
background figure, not a different character). Respond with ONLY JSON:
{"present": true|false, "prominent": true|false, "pose": "<3-6 word pose/expression>", "bbox": [x0,y0,x1,y1]}
bbox = his bounding box as FRACTIONS of width/height in 0..1 (or null if absent). No prose."""


def _key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k:
        env = Path(r"C:\Users\bradu\Documents\PermitHub-API\.env")
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    k = line.split("=", 1)[1].strip().strip('"')
    if not k:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    return k


def detect(img_path: Path, timeout=120) -> dict:
    mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}]}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = json.loads(r.read())["choices"][0]["message"]["content"]
            return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                time.sleep(15 * (attempt + 1))
                continue
            raise


def crop(img: Image.Image, bbox, pad=0.08) -> Image.Image:
    w, h = img.size
    x0, y0, x1, y1 = (float(v) for v in bbox)
    mx = max(x0, y0, x1, y1)
    norm = 1.0 if mx <= 1.5 else (1000.0 if mx <= 1000 else max(w, h))  # 0..1, 0..1000, or pixels
    px0, py0, px1, py1 = x0 / norm * w, y0 / norm * h, x1 / norm * w, y1 / norm * h
    if px1 < px0:
        px0, px1 = px1, px0
    if py1 < py0:
        py0, py1 = py1, py0
    dw, dh = (px1 - px0) * pad, (py1 - py0) * pad
    box = (max(0, int(px0 - dw)), max(0, int(py0 - dh)), min(w, int(px1 + dw)), min(h, int(py1 + dh)))
    if box[2] - box[0] < 64 or box[3] - box[1] < 64:
        return None
    return img.crop(box)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--review", action="store_true")
    args = ap.parse_args(argv)

    idxfile = args.out / "_mine_index.jsonl"
    if args.review:
        rows = [json.loads(l) for l in idxfile.read_text(encoding="utf-8").splitlines()] if idxfile.exists() else []
        kept = [r for r in rows if r.get("kept")]
        print(f"{len(kept)} avatar crops kept (of {len(rows)} panels scanned):")
        for r in kept:
            print(f"  {r['base']}  pose='{r.get('pose','')}'")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    imgs = sorted([p for p in (args.src / "images").iterdir()
                   if p.suffix.lower() in (".png", ".jpg", ".jpeg")])
    if args.limit:
        imgs = imgs[:args.limit]
    done = set()
    if idxfile.exists():
        done = {json.loads(l)["base"] for l in idxfile.read_text(encoding="utf-8").splitlines()}
    kept = 0
    for p in imgs:
        base = p.stem
        if base in done:
            continue
        try:
            d = detect(p)
        except Exception as e:
            print(f"  ! {base}: {e} (not indexed — will retry next run)")
            continue
        rec = {"base": base, "kept": False}
        if d.get("present") and d.get("prominent") and d.get("bbox"):
            try:
                c = crop(Image.open(p).convert("RGB"), d["bbox"])
            except Exception:
                c = None
            if c is not None:
                c.save(args.out / f"{base}.png")
                pose = re.sub(r"[^a-zA-Z0-9 ,]", "", (d.get("pose") or "")).strip()[:50]
                (args.out / f"{base}.txt").write_text(f"brdmc, {pose}" if pose else "brdmc", encoding="utf-8")
                rec.update(kept=True, pose=pose)
                kept += 1
                print(f"  ✓ {base}  brdmc, {pose}")
        with idxfile.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        time.sleep(1.5)
    print(f"\nmined {kept} avatar crops -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
