# Rendering ai-toolkit Flux LoRAs in ComfyUI ("align ai-toolkit ↔ ComfyUI")

## TL;DR — they're already aligned; fix the render graph, not the trainer

ai-toolkit (ostris) saves Flux LoRAs in the **standard diffusers/PEFT format**, and a
current ComfyUI loads that format **natively with zero conversion**. The 2026-06-15
"lora key not loaded / patched no layers" failure was **not** a training-output
problem — it was the LoRA being applied to a **non-standard model node** (Kijai's
fp8-wrapped UNet), whose internal module keys don't match ComfyUI's standard
`diffusion_model.*`, so the key map had nothing to bind to.

## Evidence (verified 2026-06-16)

- **ai-toolkit emits** (from `models/stripe/hand/char/stripe_char_v2.safetensors`,
  ai-toolkit 0.10.11): keys like
  `transformer.single_transformer_blocks.N.attn.to_q.lora_A.weight` /
  `.lora_B.weight` — 988 tensors, single `transformer.` prefix, PEFT `lora_A/lora_B`
  suffix pairs. `__metadata__.format = pt`, `ss_base_model_version = flux.1`.
- **ComfyUI maps it natively**:
  - `comfy/lora.py:268-272` — `flux_to_diffusers(...)` then
    `key_map["transformer.{}".format(k[:-len(".weight")])] = to`  *("regular diffusers
    flux lora format")*.
  - `comfy/weight_adapter/lora.py:177-179` — `diffusers2_lora = "{}.lora_B.weight"`
    handles the PEFT `.lora_A/.lora_B` suffix.
  - `comfy/lora_convert.py` — only special-cases BFL-control / Wan-Fun / USO; the
    `transformer.*` diffusers format is passed straight through to the native mapper.
  - Local installs are recent enough (autostudio ComfyUI git 2026-06-02;
    comfy/ComfyUI 2026-05-24) — both support it.

## The correct ComfyUI graph (native Flux path)

```
Load Diffusion Model (UNETLoader)   unet: flux1-dev (fp8_e4m3fn or bf16)   ─┐
  └─> LoraLoaderModelOnly           lora: stripe_char_v7_nb.safetensors      │ MODEL
                                    strength_model: ~0.8–1.0                 │
DualCLIPLoader  type: flux  (t5xxl_fp16 + clip_l) ─> CLIPTextEncode ─┐ COND │
                                                     FluxGuidance 3.5 ┘     │
EmptySD3LatentImage 1024x1024 ─┐                                            │
                    KSampler (or SamplerCustomAdvanced) <── MODEL,COND,LATENT
                    └─> VAEDecode (ae.safetensors) ─> SaveImage
```

Key points that make ai-toolkit LoRAs bind:
1. Load the base model with the **native `Load Diffusion Model` (UNETLoader)** node
   (or a standard GGUF UNet loader). **Do NOT** route through Kijai's fp8 wrapper /
   custom fp8-scaled UNet nodes — those rename the unet keys and the LoRA won't bind.
2. Apply the LoRA with **`LoraLoaderModelOnly`** (Flux char LoRAs touch the unet only;
   text-encoder training is off in our config).
3. Sanity check: ComfyUI prints `loaded completely` and, on a mismatch, a
   `lora key not loaded` count. After this fix that count should be **0**.

## Inference notes specific to Stripe (carry over from prior findings)

- **Flux bare triggers are inert** — `strp` alone won't fire the character. Describe
  the subject in the prompt *and* include the trigger, e.g.
  `strp, a fat bald man with a Norwood-VII horseshoe fringe, very hairy body,
  sunglasses, gold chain, stained white speedo`.
- Layer with the **brdrck style LoRA** + a described B&W ink line-art style block for
  the locked look.

## If you ever MUST use a GGUF/Kijai/older-ComfyUI model

Convert the diffusers LoRA to kohya `lora_unet_*` format (a small offline remap of
`transformer.* .lora_A/.lora_B` → `diffusion_model.* .lora_down/.lora_up`). Not needed
for the native path above — ask and I'll add `lora_to_comfy.py`.
