#!/usr/bin/env python3
r"""set_banner_text.py - re-letter BOTH lines of the City Hall banner with a real typeface (Oswald), keeping the
fabric, its folds and its light.

Third tool of the family (fix_harnomy.py swaps glyphs; set_banner_line.py re-lays one line from the banner's own
letters). This one is for wording the fabric does not contain the letters for (Z, !, comma): the two text lines
are located, cleared per column (the fabric's horizontal light and weave kept), and the new lines are set in
Oswald Medium - the same condensed grotesque family the model rendered - at the original line heights, scaled
down uniformly to fit the fabric, tinted with the banner's own letter colour and modulated by the local fabric
shading so the letters sit IN the cloth.

usage: set_banner_text.py IN.png OUT.png X0 Y0 X1 Y1 --line1 "TEXT" --line2 "TEXT" [--font-dir DIR]
                          [--quad "TLx,TLy TRx,TRy BRx,BRy BLx,BLy"] [--debug DBG.png] [--h1 F] [--h2 F]
  X0..Y1  a box around both text lines (in the rectified strip when --quad is given: fractions 0-1 allowed).
  --quad  the banner's corners when it is seen in perspective; the strip is rectified, set, and warped back.
  --h1/--h2  multiply the detected line heights (default 1.0) - use when the new line is much longer.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = "/tmp/fonts/package/files"


def runs_of(mask):
    out, s = [], None
    for i, v in enumerate(mask):
        if v and s is None:
            s = i
        if not v and s is not None:
            out.append((s, i - 1)); s = None
    if s is not None:
        out.append((s, len(mask) - 1))
    return out


def find_coeffs(src_pts, dst_pts):
    A = []
    for (x, y), (X, Y) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y])
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y])
    return np.linalg.solve(np.asarray(A, float), np.asarray(dst_pts, float).reshape(8))


def text_mask(text, px, weight, tracking_frac=0.02, ss=4):
    """Anti-aliased luminance mask of `text` in Oswald at cap-height ~px, supersampled ss x."""
    fnt = ImageFont.truetype(os.path.join(FONT_DIR, "oswald-latin-%d-normal.woff" % weight), px * ss)
    # Oswald cap height ~0.81 em at this size scale; measure to be exact
    cap = fnt.getbbox("H"); cap_h = cap[3] - cap[1]
    scale = (px * ss) / cap_h
    fnt = ImageFont.truetype(os.path.join(FONT_DIR, "oswald-latin-%d-normal.woff" % weight), int(round(px * ss * scale)))
    cap = fnt.getbbox("H")
    tracking = tracking_frac * px * ss
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    widths = [d0.textlength(ch, font=fnt) for ch in text]
    total = int(round(sum(widths) + tracking * (len(text) - 1))) + 8 * ss
    asc, desc = fnt.getmetrics()
    im = Image.new("L", (total, asc + desc + 4 * ss), 0)
    d = ImageDraw.Draw(im)
    x = 4 * ss
    for ch, wch in zip(text, widths):
        d.text((x, 2 * ss), ch, font=fnt, fill=255)
        x += wch + tracking
    a = np.asarray(im)
    ys, xs = np.nonzero(a > 8)
    im = im.crop((xs.min(), cap[1] + 2 * ss - 2, xs.max() + 1, cap[3] + 2 * ss + int(0.22 * (cap[3] - cap[1]))))   # caps + room for commas
    w, h = im.size
    return im.resize((max(1, w // ss), max(1, h // ss)), Image.LANCZOS)


def set_text(a, box, line1, line2, h1=1.0, h2=1.0, debug=None, fabric_rows=None):
    """a: float32 HxWx3 (the flat strip or the full image). box: (x0,y0,x1,y1) around both lines."""
    x0, y0, x1, y1 = box
    reg = a[y0:y1, x0:x1]
    lum = reg.mean(-1)
    bg = np.percentile(lum, 30)
    thr = bg + 0.45 * (np.percentile(lum, 97) - bg)
    ink = lum > thr
    W = x1 - x0
    prof = ink.sum(1).astype(float)
    rows = np.nonzero(prof > 0.04 * W)[0]
    t0, t1 = rows.min(), rows.max()
    lo, hi = t0 + int(0.35 * (t1 - t0)), t0 + int(0.65 * (t1 - t0))
    split = lo + int(np.argmin(prof[lo:hi + 1]))
    l1 = (t0, split - 1); l2 = (split + 1, t1)
    # trim each line's rows to where its ink really is
    def trim(r):
        rr = np.nonzero(prof[r[0]:r[1] + 1] > 0.02 * W)[0]
        return (r[0] + rr.min(), r[0] + rr.max())
    l1, l2 = trim(l1), trim(l2)
    cols = ink.any(0); xs = np.nonzero(cols)[0]
    tx0, tx1 = xs.min(), xs.max()
    centre_x = (tx0 + tx1) / 2.0
    letter_col = np.median(reg[ink], axis=0)                     # the banner's own letter colour
    print("lines rows %s / %s (box-relative); text x %d-%d; letter colour %s" % (l1, l2, tx0, tx1, letter_col.round(0)))

    # --- clear the text block: per-column blend of fabric above line 1 and below line 2 + zero-mean weave
    above = list(range(max(0, l1[0] - 8), max(1, l1[0] - 1)))
    below = list(range(min(reg.shape[0] - 1, l2[1] + 2), min(reg.shape[0], l2[1] + 8))) or [reg.shape[0] - 1]
    if fabric_rows:                                              # a named clean band of fabric (absolute rows)
        fr = list(range(fabric_rows[0] - y0, fabric_rows[1] - y0))
        above = below = fr
    cy0, cy1 = max(0, l1[0] - 2), min(reg.shape[0], l2[1] + 3)
    if fabric_rows:                                              # a hand-placed box: clear all of it
        cy0, cy1 = 1, reg.shape[0] - 1
    bg_top = reg[above].mean(0); bg_bot = reg[below].mean(0)
    tt = ((np.arange(cy0, cy1) - cy0) / float(cy1 - cy0))[:, None, None]
    base = bg_top[None] * (1 - tt) + bg_bot[None] * tt
    # weave: zero-mean texture from the fabric rows above and below the text, tiled vertically (full width)
    from scipy.ndimage import gaussian_filter
    tex_rows = np.concatenate([reg[above], reg[below]], axis=0)
    tex_rows = tex_rows - tex_rows.mean(0, keepdims=True)
    amp = float(tex_rows.std())
    rng = np.random.default_rng(901)
    noise = gaussian_filter(rng.normal(0.0, 1.0, (cy1 - cy0, W)), 0.7)
    noise = noise / max(noise.std(), 1e-6) * amp
    tex = np.repeat(noise[..., None], 3, axis=2) * np.array([1.0, 0.9, 0.95])[None, None, :]
    out = a.copy()
    out[y0 + cy0:y0 + cy1, x0:x1] = base + 0.9 * tex
    fabric = gaussian_filter(out[y0 + cy0:y0 + cy1, x0:x1].mean(-1), 5.0)   # folds and light only, no weave

    # --- typeset
    avail = (tx1 - tx0) * 1.0
    cap1 = (l1[1] - l1[0] + 1) * h1
    lines = [(line1, cap1, l1), (line2, cap1 * 0.78 * h2, l2)]   # line 2 always 78 % of line 1, as designed
    # one common scale so the lines keep their original size hierarchy
    scale = 1.0
    for text, cap_h, rr in lines:
        m = text_mask(text, max(6, int(round(cap_h))), 500)
        scale = min(scale, avail / m.width)
    masks = [text_mask(text, max(6, int(round(cap_h * scale))), 500) for text, cap_h, rr in lines]
    # vertical layout: keep each line centred on its old rows (line 2 may be smaller now)
    for (text, cap_h, rr), m in zip(lines, masks):
        mw, mh = m.size
        cap_px = mh / 1.22
        cx = int(round(centre_x - mw / 2.0)); cy = int(round((rr[0] + rr[1] + 1) / 2.0 - cap_px / 2.0))
        alpha = np.asarray(m).astype(np.float32) / 255.0
        alpha = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.35))).astype(np.float32) / 255.0
        ys0, xs0 = y0 + cy, x0 + cx
        sub = out[ys0:ys0 + mh, xs0:xs0 + mw]
        shade = gaussian_filter(sub.mean(-1), 5.0) / max(fabric.mean(), 1.0)
        col = letter_col[None, None, :] * np.clip(shade, 0.6, 1.25)[..., None]
        out[ys0:ys0 + mh, xs0:xs0 + mw] = sub * (1 - alpha[..., None]) + col * alpha[..., None]
        print("set %r at x %d-%d rows %d-%d (cap %d px)" % (text, xs0, xs0 + mw, ys0, ys0 + mh, mh))
    return out


def main():
    global FONT_DIR
    args = sys.argv[1:]
    def take(flag, n=1):
        if flag in args:
            i = args.index(flag); v = args[i + 1:i + 1 + n]; del args[i:i + 1 + n]; return v
        return None
    line1 = take("--line1")[0]; line2 = take("--line2")[0]
    fd = take("--font-dir"); FONT_DIR = fd[0] if fd else FONT_DIR
    quad = take("--quad"); dbg = take("--debug"); dbg = dbg[0] if dbg else None
    h1 = take("--h1"); h1 = float(h1[0]) if h1 else 1.0
    h2 = take("--h2"); h2 = float(h2[0]) if h2 else 1.0
    fr = take("--fabric-rows", 2); fr = (int(fr[0]), int(fr[1])) if fr else None
    src, dst = args[0], args[1]
    box = [float(v) for v in args[2:6]]
    img = Image.open(src).convert("RGB")
    if quad:
        q = [tuple(float(v) for v in p.split(",")) for p in quad[0].split()]
        TL, TR, BR, BL = q
        w = int(round(max(np.hypot(TR[0] - TL[0], TR[1] - TL[1]), np.hypot(BR[0] - BL[0], BR[1] - BL[1])) * 2))
        h = int(round(max(np.hypot(BL[0] - TL[0], BL[1] - TL[1]), np.hypot(BR[0] - TR[0], BR[1] - TR[1])) * 2))
        rect = [(0, 0), (w, 0), (w, h), (0, h)]
        flat = np.asarray(img.transform((w, h), Image.PERSPECTIVE, find_coeffs(rect, q), Image.BICUBIC)).astype(np.float32)
        b = [int(round(box[0] * w)) if box[0] <= 1 else int(box[0]), int(round(box[1] * h)) if box[1] <= 1 else int(box[1]),
             int(round(box[2] * w)) if box[2] <= 1 else int(box[2]), int(round(box[3] * h)) if box[3] <= 1 else int(box[3])]
        out = set_text(flat, tuple(b), line1, line2, h1, h2, fabric_rows=fr)
        back = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).transform(img.size, Image.PERSPECTIVE, find_coeffs(q, rect), Image.BICUBIC)
        cx = np.mean([p[0] for p in q]); cy = np.mean([p[1] for p in q])
        inset = [(cx + (p[0] - cx) * 0.985, cy + (p[1] - cy) * 0.985) for p in q]
        mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).polygon(inset, fill=255)
        res = Image.composite(back, img, mask.filter(ImageFilter.GaussianBlur(1.2)))
        dx0 = int(min(p[0] for p in q)) - 20; dx1 = int(max(p[0] for p in q)) + 20
        dy0 = int(min(p[1] for p in q)) - 20; dy1 = int(max(p[1] for p in q)) + 20
    else:
        a = np.asarray(img).astype(np.float32)
        out = set_text(a, tuple(int(v) for v in box), line1, line2, h1, h2, fabric_rows=fr)
        res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        dx0, dy0, dx1, dy1 = int(box[0]) - 20, int(box[1]) - 20, int(box[2]) + 20, int(box[3]) + 20
    res.save(dst)
    if dbg:
        c = res.crop((max(0, dx0), max(0, dy0), dx1, dy1)); c.resize((c.width * 3, c.height * 3), Image.LANCZOS).save(dbg)
    print("wrote", dst)


if __name__ == "__main__":
    main()
