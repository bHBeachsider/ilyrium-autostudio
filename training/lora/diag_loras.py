#!/usr/bin/env python3
"""Isolate render-path vs training: render the SAME scene through base / v1 / v2,
each with a rich style prompt and the bare trigger, and PROVE the LoRA is applied
(count lora modules + active adapters). v1 ink was known-good in ComfyUI; if v1_rich
is strong here, the diffusers path is fine and v2/char are the problem. If v1_rich is
ALSO weak, the diffusers path under-applies the ai-toolkit LoRAs (not a training fault).
"""
import os, torch
from diffusers import FluxPipeline

OUT = "/home/ec2-user/diag_out"; os.makedirs(OUT, exist_ok=True)
V1 = "/home/ec2-user/v1_broderick_flux.safetensors"
V2 = "/home/ec2-user/ai-toolkit/output/broderick_flux_v2/broderick_flux_v2.safetensors"
RICH = ("black and white hand-drawn ink comic illustration, bold confident ink linework, "
        "loose cross-hatching, a man talking on a telephone at a desk looking shocked, white background")
BARE = "brdrck style, a man talking on a telephone at a desk looking shocked"

pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16).to("cuda")


def lora_mods():
    return sum(1 for n, _ in pipe.transformer.named_modules() if "lora" in n.lower())


def gen(tag, prompt, scale, seed=42):
    kw = {"joint_attention_kwargs": {"scale": scale}} if scale is not None else {}
    pipe(prompt, num_inference_steps=28, guidance_scale=3.5, height=1024, width=1024,
         generator=torch.Generator("cuda").manual_seed(seed), **kw).images[0].save(f"{OUT}/{tag}.png")
    print("saved", tag, flush=True)


gen("base_rich", RICH, None)

pipe.load_lora_weights(V1, adapter_name="v1")
print("V1 loaded: active=", pipe.get_active_adapters(), "lora_modules=", lora_mods(), flush=True)
gen("v1_rich", RICH, 1.0); gen("v1_bare", BARE, 1.0)
pipe.delete_adapters("v1")

pipe.load_lora_weights(V2, adapter_name="v2")
print("V2 loaded: active=", pipe.get_active_adapters(), "lora_modules=", lora_mods(), flush=True)
gen("v2_rich", RICH, 1.0); gen("v2_bare", BARE, 1.0)
print("DONE", flush=True)
