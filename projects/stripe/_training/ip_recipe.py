#!/usr/bin/env python3
"""Lock the combined recipe: IP-Adapter (identity from user ref) + brdrck style LoRA (B&W cartoon)
+ explicit white-speedo prompt. Sweep IP scale 0.4 vs 0.6 to find the point where identity carries
but the B&W cartoon style + speedo win. 4 images."""
import os, torch
from diffusers import FluxPipeline
from diffusers.utils import load_image

OUT = "/home/ec2-user/iprecipe_out"; os.makedirs(OUT, exist_ok=True)
pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16).to("cuda")
pipe.load_lora_weights("/home/ec2-user/loras/broderick_flux_v2.safetensors", adapter_name="brdrck")
pipe.set_adapters(["brdrck"], adapter_weights=[0.8])
pipe.load_ip_adapter("XLabs-AI/flux-ip-adapter", weight_name="ip_adapter.safetensors",
                     image_encoder_pretrained_model_name_or_path="openai/clip-vit-large-patch14")
ref = load_image("/home/ec2-user/refs/stripe_front.jpg")

STYLE = "sparse clean black and white cartoon, confident ink outlines, flat, white background"
DESC = ("a fat bald man in a tight white speedo, dark sunglasses, gold chain, gold bracelet, "
        "brown sneakers, light body hair")
poses = ["standing facing forward, full body", "pointing, full body"]
i = 0
for scale in [0.4, 0.6]:
    pipe.set_ip_adapter_scale(scale)
    for pose in poses:
        p = f"{STYLE}, {DESC}, {pose}"
        img = pipe(p, ip_adapter_image=ref, num_inference_steps=28, guidance_scale=3.5,
                   height=1024, width=1024, generator=torch.Generator("cuda").manual_seed(10 + i)).images[0]
        tag = f"s{int(scale*10)}_{pose.split(',')[0].replace(' ', '_')}"
        img.save(f"{OUT}/{tag}.png"); print("saved", tag, flush=True); i += 1
print("IPRECIPE_DONE", flush=True)
