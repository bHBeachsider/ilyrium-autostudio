#!/usr/bin/env python3
"""STRIPE strip v2 with strp char LoRA + brdrck style LoRA AND strong explicit hair wording
(the lesson: describe features even with the LoRA). Panels 1/2/3/5 once each; panel 4 gets
4 rear-view candidates to brute-force the orientation. One Flux load."""
import os, sys
sys.path.insert(0, "/home/ec2-user/pkg")
from satirist import render

OUT = "/home/ec2-user/stripe_out"; os.makedirs(OUT, exist_ok=True)
STYLE = ("clean confident black ink outlines, sparse minimal linework, simple stylized cartoon "
         "figure, flat gray tone, lots of white space, black and white, white background")
DESC = ("strp, Stripe a fat bald man, a VERY hairy body covered in thick dark hair on his chest "
        "belly back arms and legs, dark sunglasses, a thick gold chain")
LORA = [("/home/ec2-user/loras/stripe_char.safetensors", 0.9),
        ("/home/ec2-user/loras/broderick_flux_v2.safetensors", 0.8)]

panels = {
    1: "lounging back on a poolside deck chair gesturing grandly, two bikini women on nearby loungers, a palm tree, mostly empty white background",
    2: "standing by the pool pointing back over his shoulder at a big gaudy mansion, two bikini women watching, mostly empty white background",
    3: "clutching his head with both hands in mock agony, three simple wooden signposts pointing different directions, mostly empty white background",
    5: "facing forward winking and giving an exaggerated thumbs up toward the viewer, two bikini women behind him giggling and pointing, mostly empty white background",
}
jobs = []
for n, scene in panels.items():
    p = render.compose_prompt(scene, style_block=STYLE, avatar_desc=DESC, trigger="strp")
    jobs.append((p, f"{OUT}/panel{n}.png", 60 + n))

REAR = ("seen from directly behind, his back and large bare buttocks facing the camera, head turned "
        "away from the viewer, a brown vertical stain down the centerline of the white speedo seat "
        "along the butt crack, two bikini women to the side recoiling with shocked faces, mostly "
        "empty white background")
for k in range(4):
    p = render.compose_prompt(REAR, style_block=STYLE, avatar_desc=DESC, trigger="strp")
    jobs.append((p, f"{OUT}/panel4_{chr(97 + k)}.png", 200 + k))

render.render_flux_panels(jobs, loras=LORA)
print("STRIPE_LORA2_DONE", flush=True)
