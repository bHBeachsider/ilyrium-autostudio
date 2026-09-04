#!/usr/bin/env python3
r"""set_banner_line.py - re-typeset one line of the City Hall banner from the banner's OWN glyphs.

Companion to fix_harnomy.py (NH-USA-033). nano-banana-pro cannot be trusted with the banner text, so once
the plates are LOCKED any wording change is done in pixels: every capital the new line needs already exists
on the fabric in the right font, weight, colour and light. This script
  1. finds both text lines of the banner inside a rough box (rows with pale ink on mauve),
  2. segments each line into glyph runs from the column ink profile and labels them with the known text,
  3. clears the target line with fabric sampled from the same rows,
  4. lays the new text from those glyphs, with the line's own letter and word spacing, centred, scaled
     down uniformly only if it would not fit the banner's text width.

usage: set_banner_line.py IN.png OUT.png X0 Y0 X1 Y1 --line1 "TEXT" --line2 "TEXT" --set 2 "NEW TEXT"
       [--scale 0.9] [--debug DBG.png]
  X0..Y1 is a box around BOTH lines of the banner. --line1/--line2 are what the banner currently says
  (used to label glyphs; spaces are ignored). Every character of NEW TEXT other than space must occur in
  one of the two lines.
"""
import sys
import numpy as np
from PIL import Image


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


def segment_line(ink, r0, r1, x0):
    """Glyph runs (absolute x) on rows r0..r1 of the ink mask; runs split by <=1 px are merged."""
    cols = ink[r0:r1 + 1].any(0)
    runs = runs_of(cols)
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= 1:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    return [(x0 + a, x0 + b) for a, b in merged if b - a >= 1]


def split_merged(runs, ink, r0, r1, x0, want):
    """Kerned pairs (A-Y, A-T, -T) touch at this resolution and come out as one run. While we have fewer
    runs than characters, split the widest run at its weakest interior column."""
    runs = list(runs)
    while len(runs) < want:
        widths = [b - a for a, b in runs]
        med = float(np.median(widths))
        i = int(np.argmax(widths))
        a, b = runs[i]
        if b - a < 1.4 * med:
            break
        col = ink[r0:r1 + 1, a - x0:b - x0 + 1].sum(0).astype(float)
        lo, hi = int(0.25 * (b - a)), int(0.75 * (b - a))
        j = lo + int(np.argmin(col[lo:hi + 1]))
        runs[i:i + 1] = [(a, a + j - 1), (a + j + 1, b)] if col[j] == 0 else [(a, a + j), (a + j + 1, b)]
    return runs


def label(runs, text):
    chars = [c for c in text if c != " "]
    if len(runs) != len(chars):
        raise SystemExit("line %r: found %d glyph runs for %d characters - adjust the box or the text\n  runs: %s"
                         % (text, len(runs), len(chars), runs))
    return list(zip(chars, runs))


def spacing(runs, text):
    """Median letter gap and median word gap of a labelled line."""
    chars = [c for c in text]
    gaps_l, gaps_w = [], []
    ri = 0
    for i in range(1, len(chars)):
        if chars[i] == " ":
            continue
        if chars[i - 1] == " ":
            gaps_w.append(runs[ri + 1][0] - runs[ri][1]); ri += 1
        else:
            gaps_l.append(runs[ri + 1][0] - runs[ri][1]); ri += 1
    return float(np.median(gaps_l)), float(np.median(gaps_w)) if gaps_w else 3 * float(np.median(gaps_l))


def main():
    args = sys.argv[1:]
    def take(flag, n=1):
        if flag in args:
            i = args.index(flag); vals = args[i + 1:i + 1 + n]; del args[i:i + 1 + n]; return vals
        return None
    line1 = take("--line1")[0]; line2 = take("--line2")[0]
    which, newtext = take("--set", 2); which = int(which)
    dbg = take("--debug"); dbg = dbg[0] if dbg else None
    scale_cap = take("--scale"); scale_cap = float(scale_cap[0]) if scale_cap else 1.0
    src, dst = args[0], args[1]
    x0, y0, x1, y1 = (int(v) for v in args[2:6])

    img = Image.open(src).convert("RGB")
    a = np.asarray(img).astype(np.float32)
    reg = a[y0:y1, x0:x1]
    lum = reg.mean(-1)
    bg = np.percentile(lum, 30)
    thr = bg + 0.45 * (np.percentile(lum, 97) - bg)
    ink = lum > thr
    rows = ink.sum(1) > max(3, 0.02 * ink.shape[1])
    bands = [b for b in runs_of(rows) if b[1] - b[0] >= 6]
    bands = sorted(bands, key=lambda b: -ink[b[0]:b[1] + 1].sum())[:2]
    bands = sorted(bands)
    if len(bands) != 2:
        raise SystemExit("expected two text lines in the box, found %d: %s" % (len(bands), bands))
    (l1r0, l1r1), (l2r0, l2r1) = bands
    pad = 2
    L = {}
    for k, (r0, r1, text) in {1: (l1r0, l1r1, line1), 2: (l2r0, l2r1, line2)}.items():
        r0 = max(0, r0 - pad); r1 = min(ink.shape[0] - 1, r1 + pad)
        runs = segment_line(ink, r0, r1, x0)
        runs = split_merged(runs, ink, r0, r1, x0, len([c for c in text if c != " "]))
        L[k] = dict(rows=(y0 + r0, y0 + r1 + 1), runs=runs, text=text, glyphs=label(runs, text))
        print("line %d rows %d-%d: %d glyphs %s" % (k, y0 + r0, y0 + r1, len(runs), text))

    # glyph atlas: char -> list of (line, x-run); prefer glyphs from the target line (same size/light)
    atlas = {}
    for k in (which, 3 - which):
        for c, run in L[k]["glyphs"]:
            atlas.setdefault(c, []).append((k, run))
    missing = sorted({c for c in newtext if c != " " and c not in atlas})
    if missing:
        raise SystemExit("glyphs not on the banner: %s" % missing)

    T = L[which]
    ty0, ty1 = T["rows"]
    th = ty1 - ty0
    gap_l, gap_w = spacing(T["runs"], T["text"])
    other = L[3 - which]
    oh = other["rows"][1] - other["rows"][0]

    def glyph(c):
        k, (gx0, gx1) = atlas[c][0]
        gy0, gy1 = L[k]["rows"]
        g = a[gy0:gy1, gx0:gx1 + 1]
        if k != which:                                  # bring the other line's glyph to this line's height
            s = th / (gy1 - gy0)
            im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).resize(
                (max(1, int(round(g.shape[1] * s))), th), Image.LANCZOS)
            g = np.asarray(im).astype(np.float32)
        return g

    glyphs = [None if c == " " else glyph(c) for c in newtext]
    nat_w = sum(gap_w if g is None else g.shape[1] for g in glyphs) + gap_l * sum(
        1 for i in range(1, len(newtext)) if newtext[i] != " " and newtext[i - 1] != " ")
    # available width: the banner's text width = the wider line's extent
    wide = max(L.values(), key=lambda d: d["runs"][-1][1] - d["runs"][0][0])
    avail = (wide["runs"][-1][1] - wide["runs"][0][0]) * 1.02
    scale = min(scale_cap, avail / nat_w, 1.0)
    print("natural width %.0f px, available %.0f px -> scale %.3f" % (nat_w, avail, scale))
    if scale < 1.0:
        def shrink(g):
            im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))
            return np.asarray(im.resize((max(1, int(round(g.shape[1] * scale))),
                                         max(1, int(round(g.shape[0] * scale)))), Image.LANCZOS)).astype(np.float32)
        glyphs = [None if g is None else shrink(g) for g in glyphs]
        gap_l *= scale; gap_w *= scale
    line_w = sum(gap_w if g is None else g.shape[1] for g in glyphs) + gap_l * sum(
        1 for i in range(1, len(newtext)) if newtext[i] != " " and newtext[i - 1] != " ")
    centre = (wide["runs"][0][0] + wide["runs"][-1][1]) / 2.0
    xs = centre - line_w / 2.0

    out = a.copy()
    # clear the target line. The fabric is lit unevenly across the banner, so a single tiled strip shows as
    # a box; instead rebuild each column from the fabric ABOVE line 1 and BELOW line 2 at that same x
    # (a vertical blend that keeps the horizontal light), plus zero-mean texture from the left margin.
    top_r0, top_r1 = L[1]["rows"][0] - 9, L[1]["rows"][0] - 2
    bot_r0, bot_r1 = L[2]["rows"][1] + 2, L[2]["rows"][1] + 9
    cy0, cy1 = ty0 - 1, ty1 + 1
    cx0 = int(min(T["runs"][0][0] - 4, np.floor(xs) - 4))
    cx1 = int(max(T["runs"][-1][1] + 5, np.ceil(xs + line_w) + 5))
    bg_top = a[top_r0:top_r1, cx0:cx1].mean(0)                       # (w, 3) per-column colour above line 1
    bg_bot = a[bot_r0:bot_r1, cx0:cx1].mean(0)                       # per-column colour below line 2
    tt = ((np.arange(cy0, cy1) - (top_r1 - 1)) / float(bot_r0 - (top_r1 - 1)))[:, None, None]
    base = bg_top[None] * (1 - tt) + bg_bot[None] * tt
    fx0 = wide["runs"][0][0] - 6
    fx1 = T["runs"][0][0] - 3
    if fx1 - fx0 < 12:
        fx0 = T["runs"][-1][1] + 3; fx1 = wide["runs"][-1][1] + 6
    strip = a[cy0:cy1, fx0:fx1]
    tex = strip - strip.mean(0, keepdims=True)                       # zero-mean weave
    tex = np.hstack([tex] * ((cx1 - cx0) // tex.shape[1] + 2))[:, :cx1 - cx0]
    out[cy0:cy1, cx0:cx1] = base + 0.8 * tex

    # lay the glyphs, vertically centred on the target line
    x = xs
    for i, (c, g) in enumerate(zip(newtext, glyphs)):
        if g is None:
            x += gap_w; continue
        if i > 0 and newtext[i - 1] != " ":
            x += gap_l
        gh, gw = g.shape[:2]
        yy = int(round(ty0 + (th - gh) / 2.0)); xx = int(round(x))
        gl = g.mean(-1)
        b = np.percentile(gl, 15); k = np.percentile(gl, 90)
        # dead zone above the glyph's own fabric so its box never shows; full ink by 65 % of the way up
        alpha = np.clip((gl - (b + 0.18 * (k - b))) / max(0.5 * (k - b), 1.0), 0, 1)[..., None]
        out[yy:yy + gh, xx:xx + gw] = out[yy:yy + gh, xx:xx + gw] * (1 - alpha) + g * alpha
        x += gw
    print("set line %d: %r  (x %.0f-%.0f, rows %d-%d)" % (which, newtext, xs, xs + line_w, ty0, ty1))
    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    res.save(dst)
    if dbg:
        bx0 = int(min(xs, wide["runs"][0][0])) - 16; bx1 = int(max(xs + line_w, wide["runs"][-1][1])) + 16
        by0 = L[1]["rows"][0] - 10; by1 = L[2]["rows"][1] + 10
        crop = res.crop((bx0, by0, bx1, by1))
        crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS).save(dbg)


if __name__ == "__main__":
    main()
