#!/usr/bin/env python3
"""Render validation grids for the two Broderick LoRAs on the GPU box.

CHAR (brdmc): the 4 config sample poses -> identity-consistency check.
STYLE v2 (brdrck): bare "brdrck style" trigger on its own (+ one no-trigger control)
-> the test that the caption-binding fix worked (trigger fires without rich style words).
Outputs PNGs to ~/render_out/.
"""
import os, torch
from diffusers import FluxPipeline

OUT = "/home/ec2-user/render_out"
os.makedirs(OUT, exist_ok=True)
CHAR = "/home/ec2-user/ai-toolkit/output/broderick_char/broderick_char.safetensors"
STYLE = "/home/ec2-user/ai-toolkit/output/broderick_flux_v2/broderick_flux_v2.safetensors"

print("loading FLUX.1-dev (bf16)...", flush=True)
pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16)
pipe.to("cuda")


def render(tag, prompt, scale, seed):
    kw = {"joint_attention_kwargs": {"scale": scale}} if scale is not None else {}
    img = pipe(prompt, num_inference_steps=28, guidance_scale=3.5,
               height=1024, width=1024,
               generator=torch.Generator("cuda").manual_seed(seed), **kw).images[0]
    img.save(f"{OUT}/{tag}.png")
    print("saved", tag, flush=True)


# ---- CHARACTER (brdmc) @ 0.9 ----
pipe.load_lora_weights(CHAR)
char = {
    "char_phone": "brdmc, sitting at a desk talking on a phone",
    "char_point": "brdmc, standing and pointing angrily",
    "char_shrug": "brdmc, shrugging with a deadpan expression",
    "char_walk":  "brdmc, walking down a street carrying a bag",
}
for i, (t, p) in enumerate(char.items()):
    render(t, p, 0.9, 42 + i)
pipe.unload_lora_weights()

# ---- STYLE v2 (brdrck) @ 0.85 — bare trigger ----
pipe.load_lora_weights(STYLE)
style = {
    "style_phone": "brdrck style, a man talking on a telephone at a desk, looking shocked",
    "style_argue": "brdrck style, two men arguing across a table",
    "style_dog":   "brdrck style, a dog leaping toward a startled kid in a yard",
    "style_walk":  "brdrck style, a man walking a city street carrying a grocery bag",
}
for i, (t, p) in enumerate(style.items()):
    render(t, p, 0.85, 42 + i)

# ---- CONTROL: same scene, NO trigger (should NOT be Broderick ink if trigger-bound) ----
render("style_CONTROL_noTrigger", "a man talking on a telephone at a desk, looking shocked", 0.85, 42)

print("DONE", flush=True)
