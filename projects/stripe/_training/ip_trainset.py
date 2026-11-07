#!/usr/bin/env python3
"""strp v2 training set via the locked recipe: IP-Adapter@0.6 (identity from user ref) + brdrck@0.8
(B&W cartoon) + hard speedo wording. Front/3-4/action poses use IP; rear poses use IP-scale 0
(brdrck-only) since the rear needs the proven style-only recipe + stripe. One Flux load."""
import os, torch
from diffusers import FluxPipeline
from diffusers.utils import load_image

OUT = "/home/ec2-user/ts_out"; os.makedirs(OUT, exist_ok=True)
pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16).to("cuda")
pipe.load_lora_weights("/home/ec2-user/loras/broderick_flux_v2.safetensors", adapter_name="brdrck")
pipe.set_adapters(["brdrck"], adapter_weights=[0.8])
pipe.load_ip_adapter("XLabs-AI/flux-ip-adapter", weight_name="ip_adapter.safetensors",
                     image_encoder_pretrained_model_name_or_path="openai/clip-vit-large-patch14")
ref = load_image("/home/ec2-user/refs/stripe_front.jpg")

STYLE = "sparse clean black and white cartoon, confident ink outlines, flat, white background"
DESC = ("a fat bald man wearing only a tight white speedo brief and brown sneakers, bare legs, no "
        "shorts, dark sunglasses, gold chain, gold bracelet on the wrist, light body hair")
ip_poses = {
    "ts01_front": "standing facing forward, full body",
    "ts02_threeq": "three-quarter view, one hand on hip, full body",
    "ts03_point": "pointing at the viewer, full body",
    "ts04_arms_crossed": "arms crossed, smug grin, full body",
    "ts05_shrug": "shrugging, full body",
    "ts06_laugh": "head back laughing, full body",
    "ts07_martini": "holding a martini glass, full body",
    "ts08_boast": "both arms raised boasting, full body",
    "ts09_walk": "walking, full body",
    "ts10_side": "side profile view, full body",
    "ts11_lounge": "lounging back on a pool deck chair",
    "ts12_thumbsup": "winking and giving a thumbs up, full body",
    "ts13_closeup": "close up of head and chest, smug",
    "ts14_handshake": "reaching out to shake hands, full body",
}
rear_poses = {
    "ts15_rear": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, seen from directly behind, rear view, full body",
    "ts16_rear_hips": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, rear view from behind hands on hips, full body",
    "ts17_back_walk": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, three-quarter back view walking away, full body",
    "ts18_rear_bend": "a brown vertical stain down the centerline of the white speedo seat along the butt crack, rear view bending toward a table, full body",
}
i = 0
pipe.set_ip_adapter_scale(0.6)
for tag, pose in ip_poses.items():
    img = pipe(f"{STYLE}, {DESC}, {pose}", ip_adapter_image=ref, num_inference_steps=28,
               guidance_scale=3.5, height=1024, width=1024,
               generator=torch.Generator("cuda").manual_seed(20 + i)).images[0]
    img.save(f"{OUT}/{tag}.png"); print("saved", tag, flush=True); i += 1
pipe.set_ip_adapter_scale(0.0)  # rears: brdrck-only (IP suppresses rear)
for tag, pose in rear_poses.items():
    img = pipe(f"{STYLE}, {DESC}, {pose}", ip_adapter_image=ref, num_inference_steps=28,
               guidance_scale=3.5, height=1024, width=1024,
               generator=torch.Generator("cuda").manual_seed(20 + i)).images[0]
    img.save(f"{OUT}/{tag}.png"); print("saved", tag, flush=True); i += 1
print("TS_DONE", i, flush=True)
