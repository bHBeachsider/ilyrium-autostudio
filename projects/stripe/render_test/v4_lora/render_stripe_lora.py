#!/usr/bin/env python3
"""STRIPE 5-panel strip rendered with the TRAINED strp character LoRA stacked on the brdrck
style LoRA. The char LoRA now carries Stripe's locked identity (bald Type-VII, hairy body/legs,
sunglasses, gold chain, crack-stripe), so a LIGHT description suffices and he stays consistent
across panels. Art only; balloons added by strip_compositor locally."""
import os, sys
sys.path.insert(0, "/home/ec2-user/pkg")
from satirist import render

OUT = "/home/ec2-user/stripe_out"; os.makedirs(OUT, exist_ok=True)
STYLE = ("clean confident black ink outlines, sparse minimal linework, simple stylized cartoon "
         "figure, flat gray tone shading, lots of white space, black and white, white background")
DESC = "strp, Stripe a fat bald hairy man in a white speedo, dark sunglasses, thick gold chain"
LORA = [("/home/ec2-user/ai-toolkit/output/stripe_char/stripe_char.safetensors", 0.9),
        ("/home/ec2-user/loras/broderick_flux_v2.safetensors", 0.8)]

panels = {
    1: "lounging back on a poolside deck chair gesturing grandly, two bikini women on nearby loungers, a palm tree, mostly empty white background",
    2: "standing by the pool pointing back over his shoulder at a big gaudy mansion, two bikini women watching, mostly empty white background",
    3: "clutching his head with both hands in mock agony, three simple wooden signposts pointing different directions, mostly empty white background",
    4: "a brown vertical stain down the centerline of the white speedo seat along the butt crack, seen from directly behind, rear view, two bikini women to the side recoiling with shocked faces, mostly empty white background",
    5: "facing forward winking and giving an exaggerated thumbs up toward the viewer, two bikini women behind him giggling and pointing, mostly empty white background",
}
jobs = []
for n, scene in panels.items():
    p = render.compose_prompt(scene, style_block=STYLE, avatar_desc=DESC, trigger="strp")
    jobs.append((p, f"{OUT}/panel{n}.png", 60 + n))
render.render_flux_panels(jobs, loras=LORA)
print("STRIPE_LORA_STRIP_DONE", flush=True)
