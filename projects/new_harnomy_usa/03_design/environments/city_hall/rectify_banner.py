#!/usr/bin/env python3
r"""rectify_banner.py - run set_banner_line.py on a banner seen in perspective.

Maps the banner's quad to a flat rectangle (upsampled), lets set_banner_line re-typeset a line there, and
warps the result back into the frame under a slightly inset polygon mask.

usage: rectify_banner.py IN.png OUT.png "TLx,TLy TRx,TRy BRx,BRy BLx,BLy" --line1 ... --line2 ... --set N "TEXT"
       [--scale S] [--debug DBG.png]   (the --line/--set/--scale flags are passed straight through)
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))


def find_coeffs(src_pts, dst_pts):
    """PIL PERSPECTIVE coefficients so that output pixel (x,y) samples input at H(x,y): src=output corners,
    dst=input corners."""
    A = []
    for (x, y), (X, Y) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y])
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y])
    A = np.asarray(A, dtype=float)
    b = np.asarray(dst_pts, dtype=float).reshape(8)
    return np.linalg.solve(A, b)


def main():
    args = sys.argv[1:]
    dbg = None
    if "--debug" in args:
        i = args.index("--debug"); dbg = args[i + 1]; del args[i:i + 2]
    src, dst, quad_s = args[0], args[1], args[2]
    passthru = args[3:]
    quad = [tuple(float(v) for v in p.split(",")) for p in quad_s.split()]
    TL, TR, BR, BL = quad
    img = Image.open(src).convert("RGB")
    # rectified size: keep the longest edge, upsample x2 for the glyph work
    w = int(round(max(np.hypot(TR[0] - TL[0], TR[1] - TL[1]), np.hypot(BR[0] - BL[0], BR[1] - BL[1])) * 2))
    h = int(round(max(np.hypot(BL[0] - TL[0], BL[1] - TL[1]), np.hypot(BR[0] - TR[0], BR[1] - TR[1])) * 2))
    rect = [(0, 0), (w, 0), (w, h), (0, h)]
    # rectified image: output (rect) pixel -> input (quad) coordinates
    coeffs = find_coeffs(rect, quad)
    flat = img.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    flat_p = os.path.splitext(dst)[0] + "_flat.png"
    flat.save(flat_p)
    flat_out = os.path.splitext(dst)[0] + "_flat_set.png"
    # the whole flat image is the banner: box = margins in
    box = [str(int(w * 0.02)), str(int(h * 0.05)), str(int(w * 0.98)), str(int(h * 0.97))]
    cmd = [sys.executable, os.path.join(HERE, "set_banner_line.py"), flat_p, flat_out] + box + passthru
    if dbg:
        cmd += ["--debug", os.path.splitext(dbg)[0] + "_flat.png"]
    print(" ".join(cmd[2:]))
    subprocess.run(cmd, check=True)
    # warp back: full-frame output pixel -> flat coordinates
    back_coeffs = find_coeffs(quad, rect)
    back = Image.open(flat_out).transform(img.size, Image.PERSPECTIVE, back_coeffs, Image.BICUBIC)
    # inset polygon mask, feathered
    cx = np.mean([p[0] for p in quad]); cy = np.mean([p[1] for p in quad])
    inset = [(cx + (p[0] - cx) * 0.985, cy + (p[1] - cy) * 0.94) for p in quad]
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).polygon(inset, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    out = Image.composite(back, img, mask)
    out.save(dst)
    if dbg:
        x0 = int(min(p[0] for p in quad)) - 20; x1 = int(max(p[0] for p in quad)) + 20
        y0 = int(min(p[1] for p in quad)) - 20; y1 = int(max(p[1] for p in quad)) + 20
        c = out.crop((x0, y0, x1, y1)); c.resize((c.width * 2, c.height * 2), Image.LANCZOS).save(dbg)
    print("wrote", dst)


if __name__ == "__main__":
    main()
