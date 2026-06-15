#!/usr/bin/env python3
"""Stage-6 hair v2 (Fal): SAM masks the scalp accurately, then we CARVE it to the lower-left +
lower-right band (the horseshoe sides, top excluded) — SAM accuracy + deterministic placement.
Flux Fill paints hair only in that band. No GPU box."""
import os, io, urllib.request, numpy as np
import fal_client
from PIL import Image, ImageFilter
from dotenv import load_dotenv
load_dotenv(r"C:/Users/bradu/Documents/slm-foundry/.env")
OUT = r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/refs/fal_hair2"
os.makedirs(OUT, exist_ok=True)
IMAGES = [
    r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/refs/stripe_cartoon_front_bracelet.jpg",
    r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/lora_seeds/v6/seed1_front.png",
    r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/lora_seeds/v6/seed2_threequarter.png",
]

def carve_sides(mask_img):
    a = np.array(mask_img.convert("L"))
    ys, xs = np.where(a > 127)
    if len(ys) == 0:
        return None
    sy0, sy1, sx0, sx1 = ys.min(), ys.max(), xs.min(), xs.max()
    sh, sw = sy1 - sy0, sx1 - sx0
    out = np.zeros_like(a)
    yband = a.copy(); yband[:sy0 + int(0.28 * sh), :] = 0          # drop only the top ~28% (bald crown)
    left = (np.arange(a.shape[1]) <= sx0 + 0.46 * sw)
    right = (np.arange(a.shape[1]) >= sx1 - 0.46 * sw)
    sidecol = (left | right)[None, :]
    out = np.where((yband > 127) & sidecol, 255, 0).astype(np.uint8)
    return Image.fromarray(out).filter(ImageFilter.MaxFilter(19))

def run(img_path):
    name = os.path.splitext(os.path.basename(img_path))[0]
    img_url = fal_client.upload_file(img_path)
    m = fal_client.subscribe("fal-ai/evf-sam", arguments={
        "image_url": img_url, "mask_only": True,
        "prompt": "the top half of the head, the skull and scalp above the eyebrows",
        "use_grounding_dino": False, "expand_mask": 4})
    scalp = Image.open(io.BytesIO(urllib.request.urlopen(m["image"]["url"]).read()))
    band = carve_sides(scalp)
    if band is None:
        print("NO_SCALP", name, flush=True); return
    band.save(f"{OUT}/{name}_mask.png")
    # upload carved mask
    band_url = fal_client.upload_file(f"{OUT}/{name}_mask.png")
    f = fal_client.subscribe("fal-ai/flux-pro/v1/fill", arguments={
        "image_url": img_url, "mask_url": band_url,
        "prompt": "thick solid black hair and dark sideburns clearly visible on the sides of the head above the ears, a bold black horseshoe fringe, heavy black ink, black and white cartoon line art",
        "output_format": "png", "safety_tolerance": "5", "seed": 7})
    urllib.request.urlretrieve(f["images"][0]["url"], f"{OUT}/{name}_hair.png")
    print("done", name, flush=True)

for p in IMAGES:
    run(p)
print("FAL_HAIR2_DONE", flush=True)
