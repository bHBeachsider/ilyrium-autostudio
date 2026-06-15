#!/usr/bin/env python3
"""Validation strip with strp v2 (clean speedo char LoRA) + brdrck style. One Flux load; per-panel
adapters: panels 1-3,5 = strp@0.9 + brdrck@0.8 (identity-locked speedo Stripe); panel 4 (rear gag)
= brdrck-only + full description (char LoRA over-fits front, so style-only does the rear)."""
import os, sys, torch
sys.path.insert(0, "/home/ec2-user/pkg")
from satirist import render
from diffusers import FluxPipeline

OUT = "/home/ec2-user/stripe_out"; os.makedirs(OUT, exist_ok=True)
STRP = "/home/ec2-user/loras/stripe_char_v2.safetensors"
BRDRCK = "/home/ec2-user/loras/broderick_flux_v2.safetensors"
STYLE = ("clean confident black ink outlines, sparse minimal linework, simple stylized cartoon, "
         "flat, lots of white space, black and white, white background")
DESC = ("strp, Stripe a fat bald man in a small white speedo, dark sunglasses, gold chain, gold "
        "bracelet, brown sneakers, light body hair")
DESC_REAR = ("Stripe a fat bald man in a small white speedo, dark sunglasses, gold chain, brown "
             "sneakers, light body hair")

pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16).to("cuda")
pipe.load_lora_weights(STRP, adapter_name="strp")
pipe.load_lora_weights(BRDRCK, adapter_name="brdrck")

def gen(n, scene, desc, adapters, weights, seed):
    pipe.set_adapters(adapters, adapter_weights=weights)
    p = render.compose_prompt(scene, style_block=STYLE, avatar_desc=desc, trigger="strp")
    img = pipe(p, num_inference_steps=28, guidance_scale=3.5, height=1024, width=1024,
               generator=torch.Generator("cuda").manual_seed(seed)).images[0]
    img.save(f"{OUT}/panel{n}.png"); print("saved panel", n, flush=True)

gen(1, "lounging back on a poolside deck chair gesturing grandly, two bikini women on nearby loungers, a palm tree, mostly empty white background", DESC, ["strp", "brdrck"], [0.9, 0.8], 61)
gen(2, "standing by the pool pointing back over his shoulder at a big gaudy mansion, two bikini women watching, mostly empty white background", DESC, ["strp", "brdrck"], [0.9, 0.8], 62)
gen(3, "clutching his head with both hands in mock agony, three simple wooden signposts pointing different directions, mostly empty white background", DESC, ["strp", "brdrck"], [0.9, 0.8], 63)
gen(4, "a brown vertical stain down the centerline of the white speedo seat along the butt crack, seen from directly behind, rear view, two bikini women to the side recoiling with shocked faces, mostly empty white background", DESC_REAR, ["brdrck"], [0.8], 64)
gen(5, "facing forward winking and giving an exaggerated thumbs up toward the viewer, two bikini women behind him giggling and pointing, mostly empty white background", DESC, ["strp", "brdrck"], [0.9, 0.8], 65)
print("STRIPE_V2_STRIP_DONE", flush=True)
