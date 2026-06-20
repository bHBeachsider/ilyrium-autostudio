#!/usr/bin/env python3
"""Stage-6 hair via Fal.ai (serverless — no GPU box): EVF-SAM(+GroundingDINO) text->mask of the
head-side band, then Flux Fill paints the horseshoe fringe. Stripe is bald, so we segment the
head-SIDE REGION (not 'hair', which doesn't exist yet) and negative-prompt the top/crown."""
import os, sys, urllib.request
import fal_client
from dotenv import load_dotenv

load_dotenv(r"C:/Users/bradu/Documents/slm-foundry/.env")  # sets FAL_KEY
OUT = r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/refs/fal_hair"
os.makedirs(OUT, exist_ok=True)
IMAGES = [
    r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/refs/stripe_cartoon_front_bracelet.jpg",
    r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/lora_seeds/v6/seed1_front.png",
    r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/lora_seeds/v6/seed2_threequarter.png",
]


def run(img_path):
    name = os.path.splitext(os.path.basename(img_path))[0]
    print("upload:", name, flush=True)
    img_url = fal_client.upload_file(img_path)

    mres = fal_client.subscribe("fal-ai/evf-sam", arguments={
        "image_url": img_url,
        "prompt": "the sides of the head above and around the ears and the back of the head",
        "negative_prompt": "the bald top and crown of the head, the face, the neck, the body",
        "mask_only": True,
        "use_grounding_dino": True,
        "expand_mask": 8,
    })
    mask_url = mres["image"]["url"]
    urllib.request.urlretrieve(mask_url, f"{OUT}/{name}_mask.png")
    print("  mask ok", flush=True)

    fres = fal_client.subscribe("fal-ai/flux-pro/v1/fill", arguments={
        "image_url": img_url,
        "mask_url": mask_url,
        "prompt": ("a horseshoe fringe of short dark gray hair on the sides of an otherwise bald "
                   "head, Norwood stage 6 male pattern baldness, simple black and white cartoon line art"),
        "output_format": "png",
        "safety_tolerance": "5",
        "seed": 3,
    })
    urllib.request.urlretrieve(fres["images"][0]["url"], f"{OUT}/{name}_hair.png")
    print("done:", name, flush=True)


for p in IMAGES:
    run(p)
print("FAL_HAIR_DONE", flush=True)
