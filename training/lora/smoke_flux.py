#!/usr/bin/env python3
"""End-to-end smoke test of the COMMITTED satirist Flux path: satirist.render.compose_prompt
+ satirist.render.render_flux, with the real Broderick LoRAs. Renders a CHARACTER panel
(style + char stacked, avatar injected) and a GENERAL panel (style only)."""
import os, sys
sys.path.insert(0, "/home/ec2-user/pkg")
from satirist import render  # the committed code

OUT = "/home/ec2-user/smoke_out"; os.makedirs(OUT, exist_ok=True)
STYLE = ("bold confident ink linework, loose cross-hatching, black and white hand-drawn "
         "indie comic, white background")
AVATAR = "a heavyset bald man with a full gray beard and thick black rectangular glasses"
STYLE_LORA = "/home/ec2-user/loras/broderick_flux_v2.safetensors"
CHAR_LORA = "/home/ec2-user/loras/broderick_char.safetensors"

# CHARACTER panel: style + char stacked, avatar description injected
p_char = render.compose_prompt("sitting at a desk looking shocked at a laptop",
                               style_block=STYLE, avatar_desc=AVATAR, trigger="brdrck")
print("CHAR PROMPT:", p_char, flush=True)
render.render_flux(p_char, f"{OUT}/smoke_character.png",
                   loras=[(STYLE_LORA, 0.85), (CHAR_LORA, 0.9)], seed=42)
print("saved smoke_character", flush=True)

# GENERAL panel: style only, no avatar
p_gen = render.compose_prompt("two men arguing across a table", style_block=STYLE, trigger="brdrck")
print("GEN PROMPT:", p_gen, flush=True)
render.render_flux(p_gen, f"{OUT}/smoke_general.png", loras=[(STYLE_LORA, 0.85)], seed=42)
print("saved smoke_general", flush=True)
print("SMOKE_DONE", flush=True)
