#!/usr/bin/env python3
r"""check_keyframe_geometry.py - refuse a keyframe whose structure disagrees with the blockout (NH-USA-050).

WHY THIS EXISTS
---------------
Brad, 2026-09-06, on the v9 cut: the truss upright sat mid-span in SH009 while every other shot has the uprights at
the ends of the stage. Prose is a suggestion to an image model and a clay reference is a stronger suggestion; neither
is a constraint (NH-USA-043/045/047/048). Until keyframes are generated through a depth ControlNet, the cheap defence
is to CHECK: the blockout knows where the load-bearing verticals are in world space, cameras.json knows the camera,
so their pixel columns are known before the image exists. This script projects them and asks the image whether a
vertical timber is actually there - and, just as important, whether one is somewhere it should not be.

It is a lint pass, not a renderer: it catches gross violations (an upright in the wrong third of the frame, a missing
end post, a second chair row) for free, before a $1.20 Veo render is spent on a bad still.

WHAT IT CHECKS
  1. POSTS   - for every control point tagged "post" visible in this camera, a vertical timber edge within
               --tol of its projected column; and no unexplained vertical timber elsewhere in the deck band.
  2. DECKLINE- the stage's front edge is a near-horizontal line at the projected height (the "parallel" rule).
  3. CHAIRS  - advisory: how many ink bands the chair strip holds (a second row shows up as extra bands).
             Never blocks - edge counting is not reliable enough to refuse an image on.
Each check prints PASS/FAIL with the measured and expected pixel positions, and the script exits non-zero on any FAIL
so it can gate a batch.

usage: check_keyframe_geometry.py KEY.png --shot SH009 [--cameras cameras.json] [--points control_points.json]
                                  [--tol 0.06] [--debug OUT.png]
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw


# ----------------------------------------------------------------- projection
def rot_matrix(euler_deg):
    """Blender XYZ euler (degrees) -> rotation matrix, camera looks down -Z with +Y up."""
    rx, ry, rz = (math.radians(a) for a in euler_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def project(pt, cam, res):
    """World point -> (u, v) in pixels, or None if behind the camera."""
    R = rot_matrix(cam["rotation_deg"])
    d = np.asarray(pt, float) - np.asarray(cam["location"], float)
    c = R.T @ d                       # into camera space
    if -c[2] <= 1e-6:                 # camera looks along -Z
        return None
    f = cam["lens_mm"] / cam["sensor_mm"]          # focal in sensor widths
    w, h = res
    u = w * (0.5 + f * (c[0] / -c[2]))
    v = h * (0.5 - f * (c[1] / -c[2]) * (w / h) / (w / h))   # square pixels
    v = h * 0.5 - w * f * (c[1] / -c[2])
    return u, v


# ----------------------------------------------------------------- image measures
def vertical_energy(a):
    """Column-wise strength of long vertical edges: |d/dx| summed down each column."""
    g = a.mean(-1)
    gx = np.abs(np.diff(g, axis=1))
    gx = np.pad(gx, ((0, 0), (0, 1)))
    return gx


def find_vertical_lines(a, y0, y1, x0=0, x1=None, min_frac=0.38):
    """Columns holding a vertical edge over at least min_frac of the band's height."""
    x1 = a.shape[1] if x1 is None else int(x1)
    x0 = int(max(0, x0))
    band = vertical_energy(a)[int(y0):int(y1), x0:x1]
    if band.size == 0:
        return np.zeros(a.shape[1]), []
    thr = np.percentile(band, 92)
    hit = band > max(thr, 6.0)
    hit = hit | np.roll(hit, 1, axis=1) | np.roll(hit, -1, axis=1)      # a timber edge drifts a pixel down its length
    strong = hit.sum(0) / float(band.shape[0])
    cols = x0 + np.nonzero(strong > min_frac)[0]
    runs, start = [], None
    prof = np.zeros(a.shape[1]); prof[x0:x1] = strong
    for i, c in enumerate(cols):
        if start is None:
            start = c; prev = c; continue
        if c - prev > 6:
            runs.append(((start + prev) // 2, float(prof[start:prev + 1].max()))); start = c
        prev = c
    if start is not None:
        runs.append(((start + prev) // 2, float(prof[start:prev + 1].max())))
    # a timber upright is the STRONGEST full-height vertical in the stage band; chair legs and mullions are weaker
    runs.sort(key=lambda r: -r[1])
    return prof, runs


def horizontal_line_angle(a, y_hint, x0, x1):
    """Angle (degrees) of the strongest near-horizontal edge near y_hint, over [x0,x1]."""
    g = a.mean(-1)
    gy = np.abs(np.diff(g, axis=0))
    win = 90
    y_lo, y_hi = max(0, int(y_hint - win)), min(gy.shape[0], int(y_hint + win))
    sub = gy[y_lo:y_hi, int(x0):int(x1)]
    if sub.size == 0:
        return None, None
    cols = np.arange(sub.shape[1])
    ys = np.argmax(sub, axis=0).astype(float)
    keep = sub.max(axis=0) > np.percentile(sub, 80)
    if keep.sum() < 20:
        return None, None
    m, c = np.polyfit(cols[keep], ys[keep], 1)
    return math.degrees(math.atan(m)), y_lo + c


def chair_rows(a, y0, y1, x0, x1):
    """Count horizontal bands of chair-height ink inside the deck region."""
    g = a.mean(-1)[int(y0):int(y1), int(x0):int(x1)]
    if g.size == 0:
        return 0, []
    prof = np.abs(np.diff(g, axis=0)).mean(1)
    if prof.size < 8:
        return 0, []
    prof = np.convolve(prof, np.ones(5) / 5.0, mode="same")
    thr = prof.mean() + 0.6 * prof.std()
    peaks = []
    for i in range(1, len(prof) - 1):
        if prof[i] > thr and prof[i] >= prof[i - 1] and prof[i] > prof[i + 1]:
            if not peaks or i - peaks[-1] > 8:
                peaks.append(i)
    return len(peaks), [int(y0) + p for p in peaks]



def column_profile(a, y0, y1):
    """Smoothed column profile of vertical-edge energy over a horizontal band."""
    band = vertical_energy(a)[int(max(0, y0)):int(y1)]
    if band.size == 0:
        return np.zeros(a.shape[1])
    prof = band.mean(0)
    k = max(5, a.shape[1] // 200)
    prof = np.convolve(prof, np.ones(k) / k, mode="same")
    return prof / max(prof.max(), 1e-6)


def peaks_of(prof, n=4, min_sep_frac=0.05):
    """The n strongest, well-separated peaks of a profile."""
    W = len(prof); sep = int(min_sep_frac * W)
    order = np.argsort(-prof)
    out = []
    for i in order:
        if prof[i] < 0.25:
            break
        if all(abs(i - j) > sep for j in out):
            out.append(int(i))
        if len(out) >= n:
            break
    return sorted(out)

# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--shot", required=True)
    ap.add_argument("--cameras", default="cameras.json")
    ap.add_argument("--points", default="control_points.json")
    ap.add_argument("--tol", type=float, default=0.06, help="fraction of frame width inside which a post PASSES")
    ap.add_argument("--hard", type=float, default=0.15, help="beyond this fraction it FAILS rather than warns")
    ap.add_argument("--clay", help="clay render from the same camera; enables the comparative check")
    ap.add_argument("--debug")
    args = ap.parse_args()

    cams = json.load(open(args.cameras))["cameras"]
    pts = json.load(open(args.points))
    if args.shot not in cams:
        sys.exit("[FAIL] no camera '%s' in %s" % (args.shot, args.cameras))
    cam = cams[args.shot]
    im = Image.open(args.image).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    H, W = a.shape[:2]
    res = (W, H)
    tol_px = args.tol * W
    fails, lines = 0, []

    # ---- where the blockout says the structure is, in this frame
    posts = []
    for p in pts.get("posts", []):
        top = project(p["top"], cam, res)
        base = project(p["base"], cam, res)
        if top is None or base is None:
            continue
        if -tol_px < base[0] < W + tol_px:
            posts.append(dict(name=p["name"], x=base[0], y_top=top[1], y_base=base[1]))
    deck = pts.get("deck_front", None)
    deck_px = None
    if deck:
        l = project(deck["left"], cam, res); r = project(deck["right"], cam, res)
        if l and r:
            deck_px = (l, r)

    # ---- 1. posts where they belong, and nowhere else
    band_y0 = min([p["y_top"] for p in posts], default=H * 0.3)
    band_y1 = max([p["y_base"] for p in posts], default=H * 0.8)
    strong, ranked = find_vertical_lines(a, max(0, band_y0), min(H, band_y1), 0, W)
    n_expected = max(1, len([p for p in posts if 0 <= p["x"] <= W]))
    candidates = [r[0] for r in ranked[:n_expected + 1]]          # the strongest few only
    found = [r[0] for r in ranked]
    lines.append("expected posts (px x): " + ", ".join("%s=%.0f" % (p["name"], p["x"]) for p in posts))
    lines.append("strongest verticals in the stage band (px x, strength): "
                 + (", ".join("%d(%.2f)" % (r[0], r[1]) for r in ranked[:5]) or "none"))
    # Graded, because the models hold layout to a few percent but not to the pixel: a small offset is scale drift
    # worth a human glance, a large one is the set rearranged (SH009 v9 was 36% of frame width out).
    for p in posts:
        if not (0 <= p["x"] <= W):
            continue
        if not candidates:
            fails += 1
            lines.append("  FAIL post %s expected at x=%.0f - no vertical timber anywhere in the deck band" % (p["name"], p["x"]))
            continue
        best = min(candidates, key=lambda f: abs(f - p["x"]))
        off = abs(best - p["x"]) / float(W)
        if off <= args.tol:
            lines.append("  PASS post %s at x=%.0f (found %d, %.1f%% of frame off)" % (p["name"], p["x"], best, 100 * off))
        elif off <= args.hard:
            lines.append("  WARN post %s at x=%.0f but nearest vertical is %d (%.1f%% off) - scale drift, LOOK at it"
                          % (p["name"], p["x"], best, 100 * off))
        else:
            fails += 1
            lines.append("  FAIL post %s expected at x=%.0f, nearest vertical is %d (%.1f%% of frame off) - the set has moved"
                          % (p["name"], p["x"], best, 100 * off))
    expected_cols = [p["x"] for p in posts if 0 <= p["x"] <= W]
    for f in candidates:
        if expected_cols and min(abs(f - e) for e in expected_cols) > args.hard * W:
            # ignore verticals outside the deck's horizontal span (columns, lampposts, buildings)
            if deck_px and min(deck_px[0][0], deck_px[1][0]) < f < max(deck_px[0][0], deck_px[1][0]):
                lines.append("  WARN vertical at x=%d inside the stage span with no post in the blockout - LOOK at it" % f)

    # ---- 2. the deck front edge is horizontal (the "parallel" rule)
    if deck_px:
        (lx, ly), (rx, ry) = deck_px
        want = math.degrees(math.atan((ry - ly) / max(abs(rx - lx), 1e-6)))
        got, _ = horizontal_line_angle(a, (ly + ry) / 2, max(0, min(lx, rx)), min(W, max(lx, rx)))
        if got is None:
            lines.append("  SKIP deck line - not enough edge to measure")
        elif abs(got - want) <= 2.5:
            lines.append("  PASS deck front edge %.1f deg (blockout %.1f)" % (got, want))
        else:
            fails += 1
            lines.append("  FAIL deck front edge %.1f deg, blockout says %.1f - the stage is not parallel" % (got, want))

    # ---- 3. one row of chairs
    ch = pts.get("chair_band")
    if ch:
        tl = project(ch["top_left"], cam, res); br = project(ch["bottom_right"], cam, res)
        if tl and br:
            n, ys = chair_rows(a, min(tl[1], br[1]), max(tl[1], br[1]), max(0, min(tl[0], br[0])), min(W, max(tl[0], br[0])))
            # advisory only: an edge profile cannot reliably separate chair backs from legs, and it fires on the
            # clay render too. It flags a frame for a human look; it never blocks one.
            if n <= 2:
                lines.append("  ok   chair band reads as %d ink band(s) - consistent with one row" % n)
            else:
                lines.append("  WARN chair band reads as %d ink bands (y=%s) - LOOK at it; the set has one row" % (n, ys))

    # ---- 4. comparative: the frame's structural verticals against the clay's, over the same band, full width
    if args.clay and os.path.exists(args.clay):
        clay = np.asarray(Image.open(args.clay).convert("RGB").resize((W, H))).astype(np.float32)
        y0 = max(0, min([p["y_top"] for p in posts], default=H * 0.2) - 0.10 * H)
        y1 = min(H, max([p["y_base"] for p in posts], default=H * 0.8) + 0.05 * H)
        pc, pk = column_profile(a, y0, y1), column_profile(clay, y0, y1)
        cp, kp = peaks_of(pc), peaks_of(pk)
        lines.append("clay verticals (px x):  " + ", ".join(str(v) for v in kp))
        lines.append("frame verticals (px x): " + ", ".join(str(v) for v in cp))
        worst, worst_at = 0.0, None
        for k in kp:
            if not cp:
                worst, worst_at = 1.0, k
                break
            off = min(abs(c - k) for c in cp) / float(W)
            if off > worst:
                worst, worst_at = off, k
        if worst_at is None:
            lines.append("  SKIP comparative - the clay holds no strong vertical")
        elif worst <= args.tol:
            lines.append("  PASS every vertical the clay has is matched within %.1f%% of frame" % (100 * worst))
        elif worst <= args.hard:
            lines.append("  WARN clay vertical at x=%d is %.1f%% of frame from the nearest one in the image" % (worst_at, 100 * worst))
        else:
            lines.append("  WARN clay vertical at x=%d has nothing within %.1f%% of frame - LOOK at it (advisory: the clay's "
                          "strongest verticals include building edges the dressed frame draws differently)" % (worst_at, 100 * worst))

    if args.debug:
        dbg = im.copy(); d = ImageDraw.Draw(dbg)
        for p in posts:
            d.line([(p["x"], p["y_top"]), (p["x"], p["y_base"])], fill=(0, 255, 0), width=4)
            d.text((p["x"] + 6, p["y_top"]), p["name"], fill=(0, 255, 0))
        for f in found:
            d.line([(f, band_y0), (f, band_y1)], fill=(255, 0, 0), width=1)
        if deck_px:
            d.line([deck_px[0], deck_px[1]], fill=(0, 200, 255), width=3)
        dbg.save(args.debug)

    print("\n".join(lines))
    print(("[FAIL] %d check(s) failed" % fails) if fails else "[OK] geometry agrees with the blockout")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
