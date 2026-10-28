#!/usr/bin/env python3
r"""transplant_line2.py - put the LOCKED plate's (already re-set) banner line 2 onto a keyframe's banner.

For a keyframe whose banner is in perspective (SH003), glyph segmentation on the keyframe itself is
unreliable; the plate's line 2 is clean, horizontal and already says the right thing. So: rectify the
keyframe's banner quad to a flat strip, clear its line-2 band with fabric rebuilt per column, key the plate's
line-2 LETTERS (alpha from luminance) in at the keyframe's line height, warp back under a feathered mask.

usage: transplant_line2.py KEY.png OUT.png "TLx,TLy TRx,TRy BRx,BRy BLx,BLy" PLATE.png px0 py0 px1 py1
       [--band r0 r1] [--debug DBG.png]
  px0..py1: box on the PLATE around its line 2 only (rows must not touch line 1).
  --band:   rows of line 2 in the FLAT keyframe banner (auto: weakest interior row of the ink profile to the
            bottom of the text).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def find_coeffs(src_pts, dst_pts):
    A = []
    for (x, y), (X, Y) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y])
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y])
    return np.linalg.solve(np.asarray(A, float), np.asarray(dst_pts, float).reshape(8))


def ink_mask(a):
    lum = a.mean(-1)
    bg = np.percentile(lum, 30)
    return lum > bg + 0.45 * (np.percentile(lum, 97) - bg), lum


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


def main():
    args = sys.argv[1:]
    dbg = None; band = None
    if "--debug" in args:
        i = args.index("--debug"); dbg = args[i + 1]; del args[i:i + 2]
    if "--band" in args:
        i = args.index("--band"); band = (int(args[i + 1]), int(args[i + 2])); del args[i:i + 3]
    key, out_p, quad_s, plate = args[0], args[1], args[2], args[3]
    px0, py0, px1, py1 = (int(v) for v in args[4:8])
    quad = [tuple(float(v) for v in p.split(",")) for p in quad_s.split()]
    TL, TR, BR, BL = quad
    img = Image.open(key).convert("RGB")
    w = int(round(max(np.hypot(TR[0] - TL[0], TR[1] - TL[1]), np.hypot(BR[0] - BL[0], BR[1] - BL[1])) * 2))
    h = int(round(max(np.hypot(BL[0] - TL[0], BL[1] - TL[1]), np.hypot(BR[0] - TR[0], BR[1] - TR[1])) * 2))
    rect = [(0, 0), (w, 0), (w, h), (0, h)]
    flat = np.asarray(img.transform((w, h), Image.PERSPECTIVE, find_coeffs(rect, quad), Image.BICUBIC)).astype(np.float32)

    # --- the keyframe's two lines in the flat strip. Residual tilt after rectification is normal (the fabric
    #     sags), so the split between the lines is fitted per column: s(x) = m*x + c.
    ink, lum = ink_mask(flat)
    prof = ink.sum(1).astype(float)
    rows = np.nonzero(prof > 0.05 * w)[0]
    t0, t1 = rows.min(), rows.max()
    lo, hi = t0 + int(0.35 * (t1 - t0)), t0 + int(0.65 * (t1 - t0))
    xs_c, ys_c = [], []
    win = max(60, w // 8)
    for cx0 in range(0, w - win + 1, win // 2):
        lp = ink[:, cx0:cx0 + win].sum(1).astype(float)
        if lp.sum() < 50:
            continue
        j = lo + int(np.argmin(lp[lo:hi + 1]))
        xs_c.append(cx0 + win / 2.0); ys_c.append(j)
    m, c = np.polyfit(xs_c, ys_c, 1)
    split = lambda x: m * x + c
    print("flat %dx%d; text rows %d-%d; split line y = %.4f x + %.1f" % (w, h, t0, t1, m, c))
    # extent of the old line 2 (below the split line)
    below = np.zeros_like(ink)
    for x in range(w):
        below[int(np.ceil(split(x))) + 1:, x] = True
    l2 = ink & below
    xs2 = np.nonzero(l2.any(0))[0]
    lx0, lx1 = xs2.min(), xs2.max()
    centre = (lx0 + lx1) / 2.0
    # line-2 height along the slant: from split to the bottom of the ink, measured at the centre column
    cc = int(centre)
    b_rows = np.nonzero(l2[:, max(0, cc - 200):cc + 200].any(1))[0]
    line_h = float(b_rows.max() - split(cc))
    print("old line 2 x %d-%d, height ~%.0f px" % (lx0, lx1, line_h))

    # --- clear everything below the split line to the bottom of the strip. Base colour per column from the
    #     fabric margin ABOVE line 1 (carries the horizontal light), re-levelled to the left margin at the
    #     band's rows; zero-mean weave on top.
    above = list(range(max(0, t0 - 9), max(1, t0 - 2)))
    mx0, mx1 = 4, max(12, lx0 - 8)
    bg_above = flat[above].mean(0)
    band_rows = slice(int(split(mx1)) + 1, h)
    level = flat[band_rows, mx0:mx1].mean((0, 1)) / np.maximum(flat[above][:, mx0:mx1].mean((0, 1)), 1.0)
    base_col = bg_above * level
    strip = flat[band_rows, mx0:mx1]
    tex = strip - strip.mean(0, keepdims=True)
    tex = np.hstack([tex] * (w // tex.shape[1] + 2))[:, :w]
    out = flat.copy()
    GAP = 5                                            # keep line 1's descending feet (the sag) intact
    for x in range(w):
        y0 = int(np.ceil(split(x))) + GAP
        n = h - y0
        out[y0:, x] = base_col[x] + 0.8 * tex[:n, x]

    # --- the plate's line 2 letters, alpha-keyed, scaled to the old line height, sheared to the split slope
    pl = np.asarray(Image.open(plate).convert("RGB")).astype(np.float32)[py0:py1, px0:px1]
    pink, plum = ink_mask(pl)
    prow = np.nonzero(pink.sum(1) > 3)[0]; pcol = np.nonzero(pink.sum(0) > 2)[0]
    pr0, pr1 = max(0, prow.min() - 1), min(pink.shape[0], prow.max() + 2)
    pc0, pc1 = max(0, pcol.min() - 2), min(pink.shape[1], pcol.max() + 3)
    glyphs = pl[pr0:pr1, pc0:pc1]
    gl = glyphs.mean(-1)
    # per-column fabric and ink levels (the plate's banner is lit unevenly): windowed percentiles
    from scipy.ndimage import percentile_filter
    b_col = percentile_filter(gl, 20, size=(gl.shape[0], 61), mode="nearest")
    k_col = percentile_filter(gl, 96, size=(gl.shape[0], 61), mode="nearest")
    span = np.maximum(k_col - b_col, 8.0)
    alpha = np.clip((gl - (b_col + 0.38 * span)) / (0.40 * span), 0, 1)
    alpha[alpha < 0.15] = 0.0
    target_h = int(round(line_h * 0.80))
    s_ = target_h / glyphs.shape[0]
    tw = int(round(glyphs.shape[1] * s_))
    if tw > w * 0.96:
        s_ *= (w * 0.96) / tw; tw = int(round(glyphs.shape[1] * s_)); target_h = int(round(glyphs.shape[0] * s_))
    G = np.asarray(Image.fromarray(np.clip(glyphs, 0, 255).astype(np.uint8)).resize((tw, target_h), Image.LANCZOS)).astype(np.float32)
    A = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).resize((tw, target_h), Image.LANCZOS)).astype(np.float32) / 255.0
    A[A < 0.08] = 0.0
    key_ink = lum[l2]
    plate_ink = gl[alpha > 0.6]
    gain = float(np.percentile(key_ink, 70) / max(np.percentile(plate_ink, 70), 1.0))
    G = np.clip(G * gain, 0, 255)
    x = int(round(centre - tw / 2.0)); x = max(2, min(x, w - tw - 2))
    # paste column by column along the slanted baseline: the letters sit (line_h - target_h)/2 below the split
    off = (line_h - target_h) / 2.0
    for i in range(tw):
        y = int(round(split(x + i) + 1 + off))
        if y < 0 or y + target_h > h:
            continue
        col_a = A[:, i][:, None]
        out[y:y + target_h, x + i] = out[y:y + target_h, x + i] * (1 - col_a) + G[:, i] * col_a
    print("letters %dx%d placed at x %d along the split line, gain %.2f" % (tw, target_h, x, gain))

    # --- warp back
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(os.path.splitext(out_p)[0] + "_flat_set.png")
    back = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).transform(img.size, Image.PERSPECTIVE,
                                                                             find_coeffs(quad, rect), Image.BICUBIC)
    cx = np.mean([p[0] for p in quad]); cy = np.mean([p[1] for p in quad])
    inset = [(cx + (p[0] - cx) * 0.985, cy + (p[1] - cy) * 0.985) for p in quad]
    mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).polygon(inset, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    res = Image.composite(back, img, mask)
    res.save(out_p)
    if dbg:
        x0 = int(min(p[0] for p in quad)) - 20; x1 = int(max(p[0] for p in quad)) + 20
        y0 = int(min(p[1] for p in quad)) - 20; y1 = int(max(p[1] for p in quad)) + 20
        c = res.crop((x0, y0, x1, y1)); c.resize((c.width * 2, c.height * 2), Image.LANCZOS).save(dbg)
    print("wrote", out_p)


if __name__ == "__main__":
    main()
