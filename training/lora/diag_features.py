#!/usr/bin/env python3
"""Prove WHY body-hair / Norwood-VII baldness won't render, and find a recipe that does.
Same character + strong hair/bald prompt, two recipes x two views (one Flux load):
  A) brdrck@0.8 + SPARSE style   (current recipe)
  B) brdrck@0.3 + DETAILED hatched style   (LoRA turned down, detail allowed)
If A is smooth/clean and B is hairy+bald, the style LoRA strength + 'sparse' block are the cause."""
import os, sys
sys.path.insert(0, "/home/ec2-user/pkg")
from satirist import render
import torch
from diffusers import FluxPipeline

OUT = "/home/ec2-user/diagfeat_out"; os.makedirs(OUT, exist_ok=True)
LORA = "/home/ec2-user/loras/broderick_flux_v2.safetensors"
DESC = ("Stripe, a fat vulgar man, a completely bald shiny dome with NO hair on top, only a "
        "horseshoe rim of hair at the back and sides (Norwood type VII), a VERY hairy body covered "
        "in thick dark hair on his chest belly back arms and legs, dark sunglasses, a white speedo, "
        "a thick gold chain")
SPARSE = "sparse clean minimal black and white cartoon, flat, white background"
DETAILED = ("detailed black and white ink comic, heavy cross-hatching and dense ink texture, "
            "underground comix linework, white background")
FRONT = "standing facing forward, full body"
REAR = ("a brown vertical stain down the centerline of the white speedo seat along the butt crack, "
        "rear view from behind, full body")

# (tag, scene, style, scale)
jobs = [
    ("A_front_sparse_0p8", FRONT, SPARSE, 0.8),
    ("A_rear_sparse_0p8",  REAR,  SPARSE, 0.8),
    ("B_front_detail_0p3", FRONT, DETAILED, 0.3),
    ("B_rear_detail_0p3",  REAR,  DETAILED, 0.3),
]
pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16).to("cuda")
pipe.load_lora_weights(LORA, adapter_name="brdrck")
for i, (tag, scene, style, scale) in enumerate(jobs):
    pipe.set_adapters(["brdrck"], adapter_weights=[scale])
    prompt = render.compose_prompt(scene, style_block=style, avatar_desc=DESC, trigger="brdrck")
    g = torch.Generator(device="cuda").manual_seed(50 + i)
    img = pipe(prompt=prompt, num_inference_steps=28, guidance_scale=3.5, height=1024, width=1024, generator=g).images[0]
    img.save(f"{OUT}/{tag}.png"); print("saved", tag, flush=True)
print("DIAGFEAT_DONE", flush=True)
