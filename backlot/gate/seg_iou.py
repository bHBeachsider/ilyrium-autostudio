#!/usr/bin/env python3
r"""seg_iou.py - does the key put the STAGE where the world puts it? Mask overlap against the seg pass (Phase 2, task 13).

The edge heuristics in check_keyframe_geometry.py find posts but cannot see a stage TURNED toward the lens
(NH-USA-052): a turned deck still has short horizontal edges. A mask can. The seg pass (usd/render_passes.py) is the
world's answer - every deck, post, beam and chair pixel in flat class colour from the shot camera. An open-vocabulary
segmenter (CLIPSeg, CPU, ~3 s a frame, no spend) answers the same question of the generated key, and the two masks
are compared per class: intersection over union, centroid offset, and the deck's principal axis angle.

The segmenter is coarse (352 px) and blobs the whole timber structure - deck, posts, beam, chairs - into one region,
so the blocking comparison is on the STRUCTURE (union of those classes in the pass) as an extent, not per part:
  structure bounding-box IoU < 0.25       FAIL   the stage is not where the world says (moved, shrunk, absent)
  structure principal axis > 12 deg off   FAIL   the stage is turned
  per-class IoUs (deck, post, beam, chair) info only - the edge check owns the exact post column
STATUS: ADVISORY. Measured on the 30 Phase 1a/1b takes against the eye (2026-09-08): CLIPSeg refused 3 correct SH006
frames (the far stage is ~1% of frame; the segmenter wanders to the paving or the window steps) and passed one
pergola take - a 13% false-reject rate on good frames. That is too high to block on, so its verdict is reported as
WARN and recorded in the take's JSON; it becomes blocking per the plan's rule (task 15) once a stronger segmenter on
the box (Grounded-SAM / SAM2, Phase 3) or a re-measure brings the false-reject rate under 5%. The measurement itself
lives in gate/regression.py so any change to thresholds re-runs it.

usage: seg_iou.py KEY.png --passes DIR [--debug OUT.png] [--json OUT.json]
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image

MODEL = "CIDAS/clipseg-rd64-refined"
PROMPTS = {
    "structure": ["a wooden rally stage with tall posts and a crossbeam", "a wooden stage platform"],
    "deck":  ["a wooden stage platform", "raw pine decking and joists"],
    "post":  ["a tall square wooden post standing upright"],
    "beam":  ["a long horizontal wooden beam"],
    "chair": ["a row of folding chairs"],
}
STRUCTURE = ("deck", "post", "beam", "chair", "steps", "podium")   # the pass classes that make up "the stage"
THRESH = {"structure": 0.35, "deck": 0.35, "post": 0.35, "beam": 0.35, "chair": 0.30}
MIN_PASS_AREA = 0.002          # class must cover >= 0.2% of the pass frame to be judged at all

_model = None


def _clipseg():
    global _model
    if _model is None:
        import torch
        from transformers import CLIPSegForImageSegmentation, CLIPSegProcessor
        _model = (CLIPSegProcessor.from_pretrained(MODEL), CLIPSegForImageSegmentation.from_pretrained(MODEL), torch)
    return _model


def predict_masks(im, classes):
    proc, model, torch = _clipseg()
    prompts = [p for c in classes for p in PROMPTS[c]]
    inp = proc(text=prompts, images=[im] * len(prompts), padding=True, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inp).logits
    probs = torch.sigmoid(logits).numpy()
    out, i = {}, 0
    for c in classes:
        n = len(PROMPTS[c]); out[c] = probs[i:i + n].max(axis=0); i += n
    return out                                       # class -> HxW float in [0,1] at the model's 352x352


def pass_masks(seg_path, seg_classes, size):
    seg = np.asarray(Image.open(seg_path).convert("RGB").resize(size, Image.NEAREST)).astype(int)
    masks = {}
    for c, (r, g, b) in seg_classes.items():
        masks[c] = (np.abs(seg[..., 0] - r) < 8) & (np.abs(seg[..., 1] - g) < 8) & (np.abs(seg[..., 2] - b) < 8)
    return masks


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def bbox(m):
    ys, xs = np.nonzero(m)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1) if len(xs) else None


def bbox_iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua else 0.0


def largest_component(m):
    """The stage is one structure: keep the biggest connected blob so a stray response (a window jamb, a kerb)
    cannot stretch the extent."""
    from scipy import ndimage
    lab, n = ndimage.label(m)
    if n <= 1:
        return m
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    return lab == (int(np.argmax(sizes)) + 1)


def centroid(m):
    ys, xs = np.nonzero(m)
    return (float(xs.mean()), float(ys.mean())) if len(xs) else None


def axis_deg(m):
    """Angle of the mask's principal axis from horizontal, in degrees (0 = the deck runs across the frame)."""
    ys, xs = np.nonzero(m)
    if len(xs) < 20:
        return None
    x = xs - xs.mean(); y = ys - ys.mean()
    cov = np.cov(np.vstack([x, y]))
    w, v = np.linalg.eigh(cov)
    vx, vy = v[:, np.argmax(w)]
    return abs(math.degrees(math.atan2(vy, vx))) % 180


def run(key_path, passes_dir, debug=None):
    meta = json.load(open(os.path.join(passes_dir, "passes.json")))
    seg_classes = {k: tuple(v) for k, v in meta["seg_classes"].items()}
    im = Image.open(key_path).convert("RGB")
    classes = ["structure"] + [c for c in PROMPTS if c in seg_classes]
    pred = predict_masks(im, classes)
    size = pred[classes[0]].shape[::-1]
    truth = pass_masks(os.path.join(passes_dir, "seg.png"), seg_classes, size)
    truth["structure"] = np.zeros_like(next(iter(truth.values())))
    for c in STRUCTURE:
        if c in truth:
            truth["structure"] |= truth[c]
    W, H = size
    res, fails, warns, lines = {}, 0, 0, []
    for c in classes:
        t = truth[c]; area = t.mean()
        p = pred[c] >= THRESH[c]
        if c == "structure":
            # ask the narrower question "is the structure where the world says, and running the way it says" -
            # look inside a band around the world's extent (10% of frame margin), keep the biggest blob there
            bt0 = bbox(t)
            if bt0:
                m = int(0.10 * W); band = np.zeros_like(p)
                band[max(0, bt0[1] - m):bt0[3] + m, max(0, bt0[0] - m):bt0[2] + m] = True
                p = largest_component(p & band)
        r = dict(pass_area=round(float(area), 4), key_area=round(float(p.mean()), 4), iou=round(iou(p, t), 3))
        if area < MIN_PASS_AREA:
            r["verdict"] = "n/a"; res[c] = r
            lines.append("  n/a  %-5s not in this frame (pass area %.2f%%)" % (c, 100 * area)); continue
        ct, cp = centroid(t), centroid(p)
        r["centroid_offset_frac"] = round(math.hypot(ct[0] - cp[0], ct[1] - cp[1]) / W, 3) if (ct and cp) else None
        if c == "structure":
            bt, bp = bbox(t), bbox(p)
            r["bbox_iou"] = round(bbox_iou(bt, bp), 3) if (bt and bp) else 0.0
            at, ap = axis_deg(t), axis_deg(p)
            r["axis_pass_deg"], r["axis_key_deg"] = at, ap
            dang = None if (at is None or ap is None) else min(abs(at - ap), 180 - abs(at - ap))
            r["axis_delta_deg"] = None if dang is None else round(dang, 1)
            if r["bbox_iou"] < 0.25:
                r["verdict"] = "WARN"; warns += 1
                lines.append("  WARN stage extent: box IoU %.2f (< 0.25) - the stage may not be where the world puts it "
                             "(advisory: 13%% false-reject measured) - LOOK at it" % r["bbox_iou"])
            elif dang is not None and dang > 12:
                r["verdict"] = "WARN"; warns += 1
                lines.append("  WARN stage axis %.0f deg in the key vs %.0f in the pass - the stage may be turned "
                             "(advisory) - LOOK at it" % (ap, at))
            else:
                r["verdict"] = "PASS"
                lines.append("  PASS stage extent: box IoU %.2f, mask IoU %.2f, axis %s vs %s deg, centroid off %.1f%% of frame"
                             % (r["bbox_iou"], r["iou"], "%.0f" % ap if ap is not None else "?",
                                "%.0f" % at if at is not None else "?", 100 * (r["centroid_offset_frac"] or 0)))
        else:
            r["verdict"] = "info"
            lines.append("  info %-5s IoU %.2f (key covers %.1f%%, pass %.1f%%)" % (c, r["iou"], 100 * r["key_area"], 100 * area))
        res[c] = r
    if debug:
        _debug_sheet(im, pred, truth, classes, seg_classes, debug)
    return dict(key=key_path, passes=passes_dir, model=MODEL, classes=res, fails=fails, warns=warns,
                verdict="FAIL" if fails else ("WARN" if warns else "PASS")), lines


def _debug_sheet(im, pred, truth, classes, seg_classes, out):
    size = pred[classes[0]].shape[::-1]
    base = np.asarray(im.resize(size)).astype(float)
    panels = []
    for c in classes:
        col = np.array(seg_classes.get(c, (255, 255, 255)), float)
        a = base.copy(); p = pred[c] >= THRESH[c]; t = truth[c]
        a[t] = a[t] * 0.4 + col * 0.6                       # world: solid class colour
        edge = p & ~np.roll(p, 1, 0) | p & ~np.roll(p, 1, 1)  # key: outline of the predicted mask
        a[edge] = (255, 255, 255)
        panels.append(Image.fromarray(a.clip(0, 255).astype(np.uint8)))
    sheet = Image.new("RGB", (size[0] * len(panels), size[1]))
    for i, p in enumerate(panels):
        sheet.paste(p, (i * size[0], 0))
    sheet.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key"); ap.add_argument("--passes", required=True, help="passes/<SHOT> dir rendered from the key's camera")
    ap.add_argument("--debug"); ap.add_argument("--json")
    a = ap.parse_args()
    res, lines = run(a.key, a.passes, a.debug)
    print("seg IoU %s vs %s" % (os.path.basename(a.key), a.passes))
    print("\n".join(lines))
    print("[%s] mask agreement %s" % (res["verdict"], {"PASS": "with the world", "WARN": "uncertain - advisory, look at the sheet"}.get(res["verdict"], "BROKEN")))
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)
    sys.exit(1 if res["verdict"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
