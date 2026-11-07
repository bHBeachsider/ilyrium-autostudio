#!/usr/bin/env python3
"""Proof: Flux IP-Adapter with the user's cartoon Stripe ref as the visual anchor -> new poses
that keep his look (bald, sunglasses, chain, bracelet, sneakers, light hair). Validates the
method before we build the full canonical sheet + retrain."""
import os, sys, torch
from diffusers import FluxPipeline
from diffusers.utils import load_image

OUT = "/home/ec2-user/ipproof_out"; os.makedirs(OUT, exist_ok=True)
pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16).to("cuda")
try:
    pipe.load_ip_adapter("XLabs-AI/flux-ip-adapter", weight_name="ip_adapter.safetensors",
                         image_encoder_pretrained_model_name_or_path="openai/clip-vit-large-patch14")
    pipe.set_ip_adapter_scale(0.7)
    print("IPADAPTER_LOADED", flush=True)
except Exception as e:
    print("IPADAPTER_LOAD_FAIL:", repr(e)[:400], flush=True)
    raise

ref = load_image("/home/ec2-user/refs/stripe_front.jpg")
BASE = "sparse black and white cartoon, white background, a fat bald man in a white speedo, sunglasses, gold chain, gold bracelet, brown sneakers"
prompts = {
    "ip_front": f"{BASE}, standing facing forward, full body",
    "ip_point": f"{BASE}, pointing at the viewer, full body",
    "ip_side":  f"{BASE}, side profile view, full body",
}
for i, (t, p) in enumerate(prompts.items()):
    img = pipe(p, ip_adapter_image=ref, num_inference_steps=28, guidance_scale=3.5,
               height=1024, width=1024, generator=torch.Generator("cuda").manual_seed(1 + i)).images[0]
    img.save(f"{OUT}/{t}.png"); print("saved", t, flush=True)
print("IPPROOF_DONE", flush=True)
