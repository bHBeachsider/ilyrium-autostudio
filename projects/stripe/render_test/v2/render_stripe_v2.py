#!/usr/bin/env python3
"""STRIPE — 5-panel comic test of the render pipeline. Uses the COMMITTED satirist code
(compose_prompt + render_flux) with the brdrck STYLE LoRA only (no char LoRA — Stripe is a
new character, described per panel for consistency). Style calibrated to the real strips:
rough scratchy B&W pen-and-pencil, grotesque underground-comix, heavy black ink, white ground.
Renders ART ONLY (no text); dialogue/balloons are added later by strip_compositor locally."""
import os, sys
sys.path.insert(0, "/home/ec2-user/pkg")
from satirist import render

OUT = "/home/ec2-user/stripe_out"; os.makedirs(OUT, exist_ok=True)
# Sparser / more stylized — calibrated to Block Party & Rock Critics: clean confident
# outlines, flat gray tone, loose lightly-sketched backgrounds, lots of white space; NOT
# dense all-over cross-hatching.
STYLE = ("clean confident black ink outlines, sparse minimal linework, simple stylized cartoon "
         "figure, flat gray tone shading, lots of white space, loose lightly sketched background, "
         "minimal detail, black and white, white background, hand-drawn comic")
DESC = ("Stripe, a fat balding middle-aged man with a big round belly, wearing a tight white "
        "speedo and a thick gold chain on his neck, smug vulgar expression")
LORA = [("/home/ec2-user/loras/broderick_flux_v2.safetensors", 0.8)]

panels = {
    1: "lounging back on a poolside deck chair gesturing grandly with one hand, two bikini women "
       "on nearby loungers, a palm tree, mostly empty white background",
    2: "standing by the pool pointing back over his shoulder at a big gaudy mansion, two bikini "
       "women watching, mostly empty white background",
    3: "clutching his head with both hands in mock agony, three simple wooden signposts pointing "
       "different directions, mostly empty white background",
    4: "seen from directly behind with his back and large rear toward the viewer, bending toward a "
       "poolside drinks table, a dark horizontal stripe stain across the seat of his tight white "
       "speedo, two bikini women to the side recoiling with shocked faces, mostly empty white background",
    5: "facing forward winking and giving an exaggerated thumbs up toward the viewer, two bikini "
       "women behind him giggling and pointing, mostly empty white background",
}

jobs = []
for n, scene in panels.items():
    p = render.compose_prompt(scene, style_block=STYLE, avatar_desc=DESC, trigger="brdrck")
    print(f"P{n}:", p, flush=True)
    jobs.append((p, f"{OUT}/panel{n}.png", 40 + n))
# ONE pipeline load for all 5 panels (avoids the per-call OOM)
render.render_flux_panels(jobs, loras=LORA)
for n in panels:
    print("saved panel", n, flush=True)
print("STRIPE_DONE", flush=True)
