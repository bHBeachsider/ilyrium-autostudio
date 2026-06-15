#!/usr/bin/env python3
"""Cheap/fast EVF-SAM mask-prompt sweep (Fal, ~$0.005 each) to find which prompt cleanly masks
the cranium/scalp on a bald cartoon head. Saves each mask to compare; no Flux Fill yet."""
import os, urllib.request, fal_client
from dotenv import load_dotenv
load_dotenv(r"C:/Users/bradu/Documents/slm-foundry/.env")
OUT = r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/refs/mask_sweep"
os.makedirs(OUT, exist_ok=True)
IMG = r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/lora_seeds/v6/seed1_front.png"

url = fal_client.upload_file(IMG)
trials = {
    "a_head_dino":     {"prompt": "the head", "use_grounding_dino": True},
    "b_scalp_dino":    {"prompt": "the bald scalp and crown and top of the head", "use_grounding_dino": True},
    "c_skull_sam":     {"prompt": "the top half of the head, the skull and scalp above the eyebrows", "use_grounding_dino": False},
    "d_head_sam":      {"prompt": "the head", "use_grounding_dino": False},
}
for tag, extra in trials.items():
    try:
        r = fal_client.subscribe("fal-ai/evf-sam", arguments={
            "image_url": url, "mask_only": True, "expand_mask": 6, **extra})
        urllib.request.urlretrieve(r["image"]["url"], f"{OUT}/{tag}.png")
        print("ok", tag, flush=True)
    except Exception as e:
        print("FAIL", tag, repr(e)[:160], flush=True)
print("SWEEP_DONE", flush=True)
