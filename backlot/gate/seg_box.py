#!/usr/bin/env python3
r"""seg_box.py - a real segmenter for the gate: Grounding DINO + SAM on the NH box (GPU), masks per class.

CLIPSeg (seg_iou.py's CPU fallback) measured 18% false-reject on good frames: at 352 px it blobs the whole square
and wanders to the paving when the stage is 1% of frame. This is the replacement, run where the GPU is:
  1. Grounding DINO (IDEA-Research/grounding-dino-tiny) finds boxes for each class from a text prompt
  2. SAM (facebook/sam-vit-base) turns each box into a pixel-exact mask
  3. masks are unioned per class and written as ONE PNG in the seg pass's class colours (SEG_CLASSES), so the
     comparison in seg_iou.py is mask-vs-mask at full resolution with no model in the loop
Output: <key>_segkey.png beside each key (+ _segkey.json: boxes, scores, timings). seg_iou.py --keymask uses it.

Detections are kept only if at least 70% of the box lies inside the world's structure band (the seg pass's extent
grown by 15% of frame), the box is under 40% of the frame, and under 3x the world's structure extent - Grounding
DINO will otherwise box all of City Hall, or the whole plaza, as "a wooden platform" (measured 2026-09-08).

usage (on the box, ComfyUI venv): seg_box.py KEY.png [KEY.png ...] [--device cuda] [--box-thr 0.22] [--text-thr 0.2]
                                  [--passes-root DIR]
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import torch
from PIL import Image

# same colours as usd/render_passes.py SEG_CLASSES (kept literal so this file runs alone on the box)
SEG_CLASSES = {"post": (255, 40, 40), "beam": (255, 140, 0), "deck": (255, 220, 0), "chair": (0, 200, 255),
               "podium": (0, 120, 255), "steps": (200, 0, 255), "furniture": (170, 110, 60), "person": (255, 255, 255)}
# Grounding DINO phrases -> class. Several phrases per class; the detector's label text is matched by keyword.
PHRASES = [("wooden stage platform", "deck"), ("timber deck", "deck"), ("wooden joists", "deck"),
           ("tall wooden post", "post"), ("wooden upright pole", "post"),
           ("horizontal wooden beam", "beam"), ("folding chair", "chair"), ("wooden podium", "podium"),
           ("wooden steps", "steps"), ("wooden desk", "furniture"), ("credenza", "furniture"), ("a person", "person"),
           ("a seated man", "person")]
KEYWORDS = {"deck": ("stage", "deck", "platform", "joist"), "post": ("post", "upright", "pole"), "beam": ("beam",),
            "chair": ("chair",), "podium": ("podium",), "steps": ("step", "stair"), "furniture": ("desk", "credenza", "table"),
            "person": ("person", "man", "woman", "figure")}

_models = {}


def load(device):
    if not _models:
        from transformers import (AutoModelForZeroShotObjectDetection, AutoProcessor, SamModel, SamProcessor)
        _models["gd_proc"] = AutoProcessor.from_pretrained("IDEA-Research/grounding-dino-tiny")
        _models["gd"] = AutoModelForZeroShotObjectDetection.from_pretrained("IDEA-Research/grounding-dino-tiny").to(device).eval()
        _models["sam_proc"] = SamProcessor.from_pretrained("facebook/sam-vit-base")
        _models["sam"] = SamModel.from_pretrained("facebook/sam-vit-base").to(device).eval()
    return _models


def classify_label(label):
    l = label.lower()
    for c, kws in KEYWORDS.items():
        if any(k in l for k in kws):
            return c
    return None


def world_band(path, passes_root, margin=0.15):
    """Where the world says the structure is (from the seg pass of the key's shot), grown by `margin` of the frame.
    Detections outside it are not 'the stage' - the question is whether the stage is where the world puts it, and
    a detector will happily box the whole City Hall as 'a wooden platform' otherwise."""
    # the shot is the key's parent folder (renders/<run>/<SHOT>/take_N.png) - "S101_SH004" is not "SH004"
    shot = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if not passes_root:
        return None
    seg_path = os.path.join(passes_root, shot, "seg.png")
    if not os.path.exists(seg_path):
        return None
    seg = np.asarray(Image.open(seg_path).convert("RGB")).astype(int)
    mask = np.zeros(seg.shape[:2], bool)
    for c in ("deck", "post", "beam", "chair", "steps", "podium", "furniture", "person"):
        r, g, b = SEG_CLASSES[c]
        mask |= (np.abs(seg[..., 0] - r) < 8) & (np.abs(seg[..., 1] - g) < 8) & (np.abs(seg[..., 2] - b) < 8)
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    h, w = mask.shape
    core = (xs.min() / w, ys.min() / h, xs.max() / w, ys.max() / h)                    # the world's structure, fractions
    band = (core[0] - margin, core[1] - margin, core[2] + margin, core[3] + margin)
    # the PLATFORM band (no posts): deck/beam/chair/steps/podium boxes must live here - a 5 m post stretches the
    # structure band up to the portico, and the detector will box the portico as "a wooden platform"
    flat = np.zeros_like(mask)
    for c in ("deck", "beam", "chair", "steps", "podium", "furniture", "person"):
        r, g, b = SEG_CLASSES[c]
        flat |= (np.abs(seg[..., 0] - r) < 8) & (np.abs(seg[..., 1] - g) < 8) & (np.abs(seg[..., 2] - b) < 8)
    fy, fx = np.nonzero(flat)
    pband = None
    if len(fx):
        pc = (fx.min() / w, fy.min() / h, fx.max() / w, fy.max() / h)
        pband = (pc[0] - margin, pc[1] - margin, pc[2] + margin, pc[3] + margin)
    return dict(core=core, band=band, core_area=(core[2] - core[0]) * (core[3] - core[1]), platform_band=pband)


def segment(path, device="cuda", box_thr=0.22, text_thr=0.2, max_boxes=40, passes_root=None, max_area=0.40):
    m = load(device)
    im = Image.open(path).convert("RGB"); W, H = im.size
    band = world_band(path, passes_root)
    text = ". ".join(p for p, _ in PHRASES) + "."
    t0 = time.time()
    inp = m["gd_proc"](images=im, text=text, return_tensors="pt").to(device)
    with torch.no_grad():
        out = m["gd"](**inp)
    res = m["gd_proc"].post_process_grounded_object_detection(out, inp.input_ids, threshold=box_thr, text_threshold=text_thr,
                                                             target_sizes=[(H, W)])[0]
    boxes, scores, labels = res["boxes"].cpu().numpy(), res["scores"].cpu().numpy(), res.get("text_labels", res.get("labels"))
    order = np.argsort(-scores)[:max_boxes]
    dets, dropped = [], []
    for i in order:
        c = classify_label(str(labels[i]))
        if not c:
            continue
        x0, y0, x1, y1 = [float(v) for v in boxes[i]]
        d = dict(cls=c, box=[x0, y0, x1, y1], score=float(scores[i]), label=str(labels[i]))
        area = (x1 - x0) * (y1 - y0) / float(W * H)
        if area > max_area:
            d["dropped"] = "box covers %.0f%% of frame" % (100 * area); dropped.append(d); continue
        if band:
            b = band["band"] if (c == "post" or not band.get("platform_band")) else band["platform_band"]
            bx0, by0, bx1, by1 = b[0] * W, b[1] * H, b[2] * W, b[3] * H
            inter = max(0, min(x1, bx1) - max(x0, bx0)) * max(0, min(y1, by1) - max(y0, by0))
            if inter / max(1.0, (x1 - x0) * (y1 - y0)) < 0.7:
                d["dropped"] = "less than 70% inside the world's structure band"; dropped.append(d); continue
            if area > 3.0 * band["core_area"] + 0.005:
                d["dropped"] = "box is %.1fx the world's structure extent (the plaza / the portico, not the stage)" % (area / max(band["core_area"], 1e-6))
                dropped.append(d); continue
        dets.append(d)
    t_det = time.time() - t0
    masks = {c: np.zeros((H, W), bool) for c in SEG_CLASSES}
    if dets:
        sam_in = m["sam_proc"](im, input_boxes=[[d["box"] for d in dets]], return_tensors="pt").to(device)
        with torch.no_grad():
            sam_out = m["sam"](**sam_in, multimask_output=False)
        mk = m["sam_proc"].image_processor.post_process_masks(sam_out.pred_masks.cpu(), sam_in["original_sizes"].cpu(),
                                                              sam_in["reshaped_input_sizes"].cpu())[0]
        mk = mk[:, 0].numpy()                                  # (n_boxes, H, W)
        for d, mm in zip(dets, mk):
            masks[d["cls"]] |= mm
    # posts and beam are thin: subtract them from the deck so the deck mask is decking, not the whole structure
    masks["deck"] &= ~(masks["post"] | masks["beam"])
    seg = np.zeros((H, W, 3), np.uint8)
    for c in ("deck", "furniture", "chair", "podium", "steps", "beam", "post", "person"):      # later classes paint over earlier
        seg[masks[c]] = SEG_CLASSES[c]
    out_png = path[:-4] + "_segkey.png"
    Image.fromarray(seg).save(out_png)
    meta = dict(key=path, detections=dets, dropped=dropped, band=band, seconds_detect=round(t_det, 2), seconds_total=round(time.time() - t0, 2),
                models="IDEA-Research/grounding-dino-tiny + facebook/sam-vit-base", box_thr=box_thr, text_thr=text_thr,
                areas={c: round(float(masks[c].mean()), 5) for c in masks})
    json.dump(meta, open(path[:-4] + "_segkey.json", "w"), indent=1)
    return out_png, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="+"); ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--box-thr", type=float, default=0.22); ap.add_argument("--text-thr", type=float, default=0.2)
    ap.add_argument("--passes-root", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "usd", "nh", "passes"),
                    help="passes/<SHOT>/seg.png gives the world's structure band; detections outside it are dropped")
    a = ap.parse_args()
    for k in a.keys:
        png, meta = segment(k, a.device, a.box_thr, a.text_thr, passes_root=a.passes_root)
        print("[OK] %s -> %s  (%d detections, %.1fs) areas %s" % (os.path.basename(k), os.path.basename(png), len(meta["detections"]),
                                                                  meta["seconds_total"], {c: v for c, v in meta["areas"].items() if v}), flush=True)


if __name__ == "__main__":
    main()
