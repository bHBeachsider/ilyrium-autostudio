#!/usr/bin/env python3
"""Expose-thighs inpaint: mask the shorts AND the upper-thigh band below them, then Flux Fill
repaints it as 'bare thighs + a small high-cut white speedo brief'. Shrinking the garment by
exposing thigh is what turns shorts into a speedo silhouette. Proof on the 3 fronts."""
import os, glob, torch, numpy as np
from PIL import Image, ImageFilter
from diffusers import FluxFillPipeline
from transformers import SegformerImageProcessor, AutoModelForSemanticSegmentation

SRC = "/home/ec2-user/fronts"; OUT = "/home/ec2-user/inpaint2_out"; os.makedirs(OUT, exist_ok=True)
proc = SegformerImageProcessor.from_pretrained("mattmdjaga/segformer_b2_clothes")
seg = AutoModelForSemanticSegmentation.from_pretrained("mattmdjaga/segformer_b2_clothes").to("cuda")

# 5/6/7 = skirt/pants/dress (the shorts); 12/13 = legs. Mask shorts + the upper-thigh band so
# the leg fabric gets repainted as skin -> high-cut speedo silhouette.
def expose_mask(img):
    inp = proc(images=img, return_tensors="pt").to("cuda")
    with torch.no_grad():
        lo = seg(**inp).logits
    up = torch.nn.functional.interpolate(lo, size=img.size[::-1], mode="bilinear", align_corners=False)
    pred = up.argmax(1)[0].cpu().numpy()
    H, W = pred.shape
    shorts = np.isin(pred, [5, 6, 7])
    legs = np.isin(pred, [12, 13])
    ys = np.where(shorts.any(axis=1))[0]
    if len(ys) == 0:
        return None
    y0, y1 = int(ys.min()), int(ys.max())
    yext = min(H, int(y1 + (y1 - y0) * 0.7))   # extend ~70% of shorts-height down into thighs
    band = np.zeros_like(shorts); band[:yext, :] = True
    mask = (shorts | (legs & band)).astype(np.uint8) * 255
    return Image.fromarray(mask).filter(ImageFilter.MaxFilter(15))

print("loading Flux Fill...", flush=True)
pipe = FluxFillPipeline.from_pretrained("black-forest-labs/FLUX.1-Fill-dev", torch_dtype=torch.bfloat16).to("cuda")
PROMPT = ("bare hairy upper thighs and a very small high-cut white speedo swim brief, most of the "
          "thighs bare and exposed skin, black and white cartoon line art, white background")
for f in sorted(glob.glob(SRC + "/*.png")):
    name = os.path.basename(f)[:-4]
    base = Image.open(f).convert("RGB").resize((1024, 1024))
    mask = expose_mask(base)
    if mask is None:
        print("NO_MASK", name, flush=True); continue
    mask.save(f"{OUT}/{name}_mask.png")
    out = pipe(prompt=PROMPT, image=base, mask_image=mask, height=1024, width=1024,
               num_inference_steps=30, guidance_scale=30,
               generator=torch.Generator("cuda").manual_seed(1)).images[0]
    out.save(f"{OUT}/{name}_speedo2.png"); print("done", name, flush=True)
print("INPAINT2_DONE", flush=True)
