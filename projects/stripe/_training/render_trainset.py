#!/usr/bin/env python3
"""Stripe LoRA TRAINING SET — ~18 consistent shots from the locked design. Speedo impeccable
(clear waistband + light tone), skid-mark on the rear angles. Identity + speedo are kept EARLY
(compose_prompt puts avatar_desc right after the short style block) so CLIP's 77-token window
doesn't drop them. Sparse Broderick-hand style, white bg. One Flux load (render_flux_panels)."""
import os, sys
sys.path.insert(0, "/home/ec2-user/pkg")
from satirist import render

OUT = "/home/ec2-user/trainset_out"; os.makedirs(OUT, exist_ok=True)
STYLE = "sparse clean black and white cartoon, confident outlines, flat gray shading, white background"
DESC = ("Stripe, a fat vulgar man, a completely bald shiny dome with NO hair on top, only a "
        "horseshoe rim of hair at the back and sides (Norwood type VII), a VERY hairy body covered "
        "in thick dark hair on his chest belly back arms and legs, dark sunglasses, a white speedo, "
        "a thick gold chain, smug expression")
LORA = [("/home/ec2-user/loras/broderick_flux_v2.safetensors", 0.8)]

scenes = {
    # front / three-quarter (clean front speedo)
    "t01_front_neutral": "standing facing forward, full body, neutral",
    "t02_front_arms_crossed": "standing facing forward, arms crossed, smug grin, full body",
    "t03_front_pointing": "standing facing forward, pointing at the viewer, full body",
    "t04_front_laughing": "standing facing forward, head back laughing, full body",
    "t05_front_shrug": "standing facing forward, shrugging, full body",
    "t06_threeq_hip": "three-quarter front view, one hand on hip, full body",
    "t07_threeq_martini": "three-quarter front view holding a martini glass, full body",
    "t08_front_closeup": "front view close up of head and chest, smug expression",
    "t09_front_boast": "standing facing forward both arms raised boasting, full body",
    # side
    "t10_side_stand": "side profile view standing, full body",
    "t11_side_lounge": "side view lounging back on a pool deck chair",
    "t12_side_walk": "side view walking, full body",
    # rear / back (skid-mark — kept first in the scene so it survives CLIP)
    "t13_rear_stand": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, rear view from behind, hands at sides, full body",
    "t14_rear_bend": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, rear view bending toward a table",
    "t15_rear_hips": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, rear view hands on hips, full body",
    "t16_back_walk": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, three-quarter back view walking away",
    "t17_rear_reach": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, rear view reaching upward",
    "t18_back_pool": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, back view standing by a pool",
}
jobs = []
for i, (name, scene) in enumerate(scenes.items()):
    p = render.compose_prompt(scene, style_block=STYLE, avatar_desc=DESC, trigger="brdrck")
    jobs.append((p, f"{OUT}/{name}.png", 100 + i))
render.render_flux_panels(jobs, loras=LORA)
print("TRAINSET_DONE", len(jobs), flush=True)
