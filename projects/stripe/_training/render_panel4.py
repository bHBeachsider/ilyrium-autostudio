#!/usr/bin/env python3
"""Panel-4 rear fix: brdrck STYLE LoRA only (NO strp char LoRA — it suppresses rear), full Stripe
description + strong rear/crack-stripe wording (the seed4 recipe that worked). 4 candidates to pick."""
import os, sys
sys.path.insert(0, "/home/ec2-user/pkg")
from satirist import render

OUT = "/home/ec2-user/p4_out"; os.makedirs(OUT, exist_ok=True)
STYLE = ("clean confident black ink outlines, sparse minimal linework, simple stylized cartoon "
         "figure, flat gray tone, lots of white space, black and white, white background")
DESC = ("Stripe, a fat man, a completely bald shiny dome with NO hair on top only a horseshoe rim "
        "at the back and sides (Norwood type VII), a VERY hairy body covered in thick dark hair on "
        "his chest belly back arms and legs, dark sunglasses, a thick gold chain")
LORA = [("/home/ec2-user/loras/broderick_flux_v2.safetensors", 0.8)]
SCENE = ("a brown vertical stain down the centerline of the white speedo seat along the butt crack, "
         "seen from directly behind, his back and large rear facing the camera, head turned away, "
         "two bikini women to the side recoiling with shocked faces, mostly empty white background")

jobs = []
for k in range(4):
    p = render.compose_prompt(SCENE, style_block=STYLE, avatar_desc=DESC, trigger="brdrck")
    jobs.append((p, f"{OUT}/p4_{chr(97 + k)}.png", 300 + k))
render.render_flux_panels(jobs, loras=LORA)
print("P4_DONE", flush=True)
