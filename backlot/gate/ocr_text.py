#!/usr/bin/env python3
r"""ocr_text.py - every text plane must read what the world says it reads (Phase 2, task 14).

Image models cannot letter (NH-USA-033/040/042): the banner comes back as a purple rectangle, a smear, or invented
words. The world knows where each text plane is (a tracked quad in the owning asset's ControlPoints, carried to
derived/control_points.json by usd/derive.py) and what it must say. This check projects the quad through the shot
camera, rectifies the strip, reads it with tesseract, and compares to the spec's lines:
  similarity >= 0.85 on every line      PASS
  plane in frame, text wrong or absent  FAIL  -> prints the exact `letter_from_plate` command (set_banner_text.py
                                                 with the projected --quad) so the fix is one paste, no judgement call
  plane not in frame / too small        n/a   (under 40 px tall after projection: OCR would be guessing)
Never asks the image model to fix lettering - the pixel tool does that, deterministically.

usage: ocr_text.py KEY.png --shot SH009 [--cameras cameras.json] [--points control_points.json] [--debug OUT.png]
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_keyframe_geometry import project  # noqa: E402

MIN_H_PX = 40
PASS_SIM = 0.85


def norm(s):
    s = s.upper().replace("’", "'").replace("‘", "'")
    return re.sub(r"[^A-Z0-9' ]+", " ", s).strip()


def rectify(im, quad, out_w=1600):
    """Perspective-rectify the quad (TL, TR, BR, BL in pixels) to a flat strip."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad
    w_top = np.hypot(x1 - x0, y1 - y0); h_l = np.hypot(x3 - x0, y3 - y0)
    out_h = max(MIN_H_PX, int(out_w * h_l / max(w_top, 1)))
    # PIL QUAD transform maps the output rectangle onto the given input quad (order: TL, BL, BR, TR)
    return im.transform((out_w, out_h), Image.QUAD, (x0, y0, x3, y3, x2, y2, x1, y1), Image.BICUBIC)


def ocr(strip):
    g = ImageOps.autocontrast(strip.convert("L"))
    if np.asarray(g).mean() < 128:                   # pale letters on a dark cloth -> invert for tesseract
        g = ImageOps.invert(g)
    g = g.resize((g.width * 2, g.height * 2), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        g.save(f.name); path = f.name
    try:
        r = subprocess.run(["tesseract", path, "-", "--psm", "6"], capture_output=True, text=True)
        return [l.strip() for l in r.stdout.splitlines() if l.strip()]
    finally:
        os.unlink(path)


def check_plane(im, cam, plane, debug=None):
    W, H = im.size
    quad = [project(c, cam, (W, H)) for c in plane["corners"]]
    if any(q is None for q in quad):
        return dict(name=plane["name"], verdict="n/a", reason="behind camera")
    xs = [q[0] for q in quad]; ys = [q[1] for q in quad]
    if max(xs) < 0 or min(xs) > W or max(ys) < 0 or min(ys) > H:
        return dict(name=plane["name"], verdict="n/a", reason="out of frame")
    h_px = max(ys) - min(ys)
    if h_px < MIN_H_PX:
        return dict(name=plane["name"], verdict="n/a", reason="too small (%.0f px tall)" % h_px, quad=quad)
    strip = rectify(im, quad)
    read = ocr(strip)
    joined = norm(" ".join(read))
    sims = []
    for want in plane["text"]:
        w = norm(want)
        # best window of the OCR text against this line (lines may wrap or merge)
        best = max([difflib.SequenceMatcher(None, w, joined[i:i + len(w) + 8]).ratio()
                    for i in range(0, max(1, len(joined) - len(w) // 2), 4)] + [0.0])
        sims.append(round(best, 3))
    verdict = "PASS" if sims and min(sims) >= PASS_SIM else "FAIL"
    if debug:
        strip.save(debug)
    return dict(name=plane["name"], verdict=verdict, quad=[[round(x, 1), round(y, 1)] for x, y in quad],
                height_px=round(h_px, 1), read=read, similarity=sims, expected=plane["text"])


def letter_cmd(key, res):
    q = " ".join("%.0f,%.0f" % (x, y) for x, y in res["quad"])
    lines = " ".join('--line%d "%s"' % (i + 1, t) for i, t in enumerate(res["expected"]))
    return ('python %s "%s" "%s" 0.04 0.10 0.96 0.90 --quad "%s" %s --ink 232,224,212'
            % (os.path.join(HERE, "letter_text_plane.py"), key, key[:-4] + "_lettered.png", q, lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key"); ap.add_argument("--shot", required=True)
    ap.add_argument("--cameras", default=os.path.join(HERE, "..", "usd", "nh", "derived", "cameras.json"))
    ap.add_argument("--points", default=os.path.join(HERE, "..", "usd", "nh", "derived", "control_points.json"))
    ap.add_argument("--debug"); ap.add_argument("--json")
    a = ap.parse_args()
    cam = json.load(open(a.cameras))["cameras"][a.shot]
    planes = json.load(open(a.points)).get("text_planes", [])
    im = Image.open(a.key).convert("RGB")
    results, fails = [], 0
    for pl in planes:
        r = check_plane(im, cam, pl, a.debug)
        results.append(r)
        if r["verdict"] == "n/a":
            print("  n/a  %s: %s" % (r["name"], r["reason"]))
        elif r["verdict"] == "PASS":
            print("  PASS %s reads as specified (similarity %s)" % (r["name"], r["similarity"]))
        else:
            fails += 1
            print("  FAIL %s reads %r (similarity %s vs expected %s)" % (r["name"], " | ".join(r["read"])[:120], r["similarity"], r["expected"]))
            print("       letter_from_plate: " + letter_cmd(a.key, r))
    if a.json:
        json.dump(dict(key=a.key, shot=a.shot, planes=results), open(a.json, "w"), indent=1)
    print("[%s] text planes" % ("FAIL" if fails else "OK"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
