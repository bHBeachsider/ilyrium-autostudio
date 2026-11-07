#!/usr/bin/env python3
"""Add Norwood Stage-6 baldness via inpaint: locate the head (segformer face/hair), mask the
crown + upper-sides band, Flux Fill paints 'bald top + thick horseshoe band of hair on the
sides'. The mask geometry controls where hair can sit. Proof on a few canonical images."""
import os, glob, torch, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from diffusers import FluxFillPipeline
from transformers import SegformerImageProcessor, AutoModelForSemanticSegmentation

SRC = "/home/ec2-user/hairsrc"; OUT = "/home/ec2-user/hair_out"; os.makedirs(OUT, exist_ok=True)
proc = SegformerImageProcessor.from_pretrained("mattmdjaga/segformer_b2_clothes")
seg = AutoModelForSemanticSegmentation.from_pretrained("mattmdjaga/segformer_b2_clothes").to("cuda")

# 11=Face, 2=Hair. Mask the crown + upper sides (where Stage-6 hair sits): a region from well
# above the face down to ~temple/ear level, slightly wider than the face.
def head_mask(img):
    inp = proc(images=img, return_tensors="pt").to("cuda")
    with torch.no_grad():
        lo = seg(**inp).logits
    up = torch.nn.functional.interpolate(lo, size=img.size[::-1], mode="bilinear", align_corners=False)
    pred = up.argmax(1)[0].cpu().numpy()
    H, W = pred.shape
    pts = np.argwhere(np.isin(pred, [11, 2]))
    if len(pts) == 0:
        return None
    ys, xs = pts[:, 0], pts[:, 1]
    fy0, fy1, fx0, fx1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
    fh, fw = fy1 - fy0, fx1 - fx0
    m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
    top = max(0, fy0 - int(0.55 * fh))   # crown-top
    bot = fy0 + int(0.30 * fh)           # down to temple / ear level
    # LEFT + RIGHT side bands only — leave the top-center bald (Stage-6 horseshoe)
    d.rectangle([fx0 - int(0.24 * fw), top, fx0 + int(0.16 * fw), bot], fill=255)
    d.rectangle([fx1 - int(0.16 * fw), top, fx1 + int(0.24 * fw), bot], fill=255)
    return m.filter(ImageFilter.MaxFilter(9))

print("loading Flux Fill...", flush=True)
pipe = FluxFillPipeline.from_pretrained("black-forest-labs/FLUX.1-Fill-dev", torch_dtype=torch.bfloat16).to("cuda")
PROMPT = ("thick short dark gray hair on the sides of the head above the ears, a horseshoe fringe, "
          "the top of the head stays bald and shiny, Norwood stage 6, black and white cartoon line art")
for f in sorted(glob.glob(SRC + "/*")):
    name = os.path.splitext(os.path.basename(f))[0]
    base = Image.open(f).convert("RGB").resize((1024, 1024))
    mask = head_mask(base)
    if mask is None:
        print("NO_HEAD", name, flush=True); continue
    mask.save(f"{OUT}/{name}_mask.png")
    out = pipe(prompt=PROMPT, image=base, mask_image=mask, height=1024, width=1024,
               num_inference_steps=30, guidance_scale=30,
               generator=torch.Generator("cuda").manual_seed(2)).images[0]
    out.save(f"{OUT}/{name}_hair.png"); print("done", name, flush=True)
print("HAIR_DONE", flush=True)
