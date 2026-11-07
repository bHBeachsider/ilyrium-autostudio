#!/usr/bin/env python3
"""Shorts->speedo inpaint. Auto-mask the lower garment with segformer_b2_clothes, then Flux Fill
paints a tight white speedo into the masked region. Proof on a few fronts before the full run.
Saves both the mask and the result so we can verify the segmentation landed on cartoons."""
import os, glob, torch, numpy as np
from PIL import Image, ImageFilter
from diffusers import FluxFillPipeline
from transformers import SegformerImageProcessor, AutoModelForSemanticSegmentation

SRC = "/home/ec2-user/fronts"; OUT = "/home/ec2-user/inpaint_out"; os.makedirs(OUT, exist_ok=True)
proc = SegformerImageProcessor.from_pretrained("mattmdjaga/segformer_b2_clothes")
seg = AutoModelForSemanticSegmentation.from_pretrained("mattmdjaga/segformer_b2_clothes").to("cuda")

# segformer_b2_clothes labels: 5=Skirt 6=Pants 7=Dress (the lower-garment classes)
def garment_mask(img):
    inp = proc(images=img, return_tensors="pt").to("cuda")
    with torch.no_grad():
        lo = seg(**inp).logits
    up = torch.nn.functional.interpolate(lo, size=img.size[::-1], mode="bilinear", align_corners=False)
    pred = up.argmax(1)[0].detach().cpu().numpy()
    m = (np.isin(pred, [5, 6, 7])).astype(np.uint8) * 255
    return Image.fromarray(m).filter(ImageFilter.MaxFilter(21))  # dilate to cover edges

print("loading Flux Fill...", flush=True)
pipe = FluxFillPipeline.from_pretrained("black-forest-labs/FLUX.1-Fill-dev", torch_dtype=torch.bfloat16).to("cuda")
PROMPT = "a small tight white speedo swim brief, bare upper thighs, black and white cartoon line art"
for f in sorted(glob.glob(SRC + "/*.png")):
    name = os.path.basename(f)[:-4]
    base = Image.open(f).convert("RGB").resize((1024, 1024))
    mask = garment_mask(base)
    mask.save(f"{OUT}/{name}_mask.png")
    px = np.array(mask).sum()
    if px == 0:
        print("NO_MASK", name, flush=True); continue
    out = pipe(prompt=PROMPT, image=base, mask_image=mask, height=1024, width=1024,
               num_inference_steps=30, guidance_scale=30,
               generator=torch.Generator("cuda").manual_seed(0)).images[0]
    out.save(f"{OUT}/{name}_speedo.png")
    print("inpainted", name, flush=True)
print("INPAINT_DONE", flush=True)
