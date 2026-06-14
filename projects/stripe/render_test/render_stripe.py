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
STYLE = ("rough scratchy pen and pencil sketch, harsh cross-hatching, heavy black ink, "
         "grotesque exaggerated underground comix caricature, crude rough linework, "
         "black and white, no color, white paper background, gritty hand-drawn")
DESC = ("Stripe, a grotesquely fat balding middle-aged man with a huge sagging belly and pot belly, "
        "wearing a too-tight white speedo and a thick heavy gold chain on his fat sweaty neck, "
        "brassy vulgar smug expression")
LORA = [("/home/ec2-user/loras/broderick_flux_v2.safetensors", 0.95)]

panels = {
    1: "lounging back on a poolside deck chair gesturing grandly with one hand, two glamorous "
       "bikini women on nearby loungers, palm trees and a swimming pool behind",
    2: "standing beside the pool pointing proudly back over his shoulder at a huge gaudy mansion, "
       "two bikini women watching, sun loungers",
    3: "clutching his head with both hands in mock agony, sweating, three crude wooden signposts "
       "pointing in different directions, poolside",
    4: "viewed from BEHIND, bending to reach a martini glass on a poolside table, a brown stain "
       "stripe across the rear seat of his tight white speedo, two bikini women behind him with "
       "shocked wide eyes and hands over mouths",
    5: "facing forward winking and giving an exaggerated thumbs up toward the viewer, two bikini "
       "women behind him giggling and pointing at his backside, poolside",
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
