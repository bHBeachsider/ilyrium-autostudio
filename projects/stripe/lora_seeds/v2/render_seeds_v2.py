#!/usr/bin/env python3
"""Stripe character-reference SEEDS — 4 canonical views to seed a Stripe character LoRA.
Sparse Broderick-hand style, white background, explicit skid-mark on the rear view so the
LoRA can learn the signature feature. One Flux load (render_flux_panels)."""
import os, sys
sys.path.insert(0, "/home/ec2-user/pkg")
from satirist import render

OUT = "/home/ec2-user/seeds_out"; os.makedirs(OUT, exist_ok=True)
STYLE = ("clean confident black ink outlines, sparse minimal linework, simple stylized cartoon "
         "figure, flat gray tone shading, lots of white space, minimal detail, black and white, "
         "white background, hand-drawn comic, full body character reference")
DESC = ("Stripe, a fat middle-aged man with a big round belly, short hair neatly parted to one "
        "side, sideburns, dark sunglasses, a tight white speedo with a clear waistband, a thick "
        "gold chain on his neck, smug vulgar expression")
SKID = "a brown skid-mark stripe running down between his buttocks along the crack of his speedo"
LORA = [("/home/ec2-user/loras/broderick_flux_v2.safetensors", 0.8)]

views = {
    "seed1_front": "standing facing forward, full body, arms relaxed at sides, neutral pose",
    "seed2_threequarter": "standing in a three-quarter front view, full body, one hand on hip",
    "seed3_side": "standing in side profile view, full body, belly in profile",
    "seed4_rear": f"{SKID}, standing with his back to the viewer, full body rear view, hands at sides",
}
jobs = []
for i, (name, scene) in enumerate(views.items()):
    p = render.compose_prompt(scene, style_block=STYLE, avatar_desc=DESC, trigger="brdrck")
    print(f"{name}: {p}", flush=True)
    jobs.append((p, f"{OUT}/{name}.png", 70 + i))
render.render_flux_panels(jobs, loras=LORA)
print("SEEDS_DONE", flush=True)
