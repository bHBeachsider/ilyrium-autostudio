#!/usr/bin/env python3
"""render_samples.py — render validation images from a trained Flux Hand LoRA.

Uses enable_model_cpu_offload() so a ~24GB Flux model fits a 24GB L4 at inference (slower, but
no OOM). One PNG per prompt. Prompts come from a file, one per line, trigger word already included.

Usage:
  python render_samples.py --base black-forest-labs/FLUX.1-dev --lora broderick_flux.safetensors \
      --prompts prompts.txt --out out_dir --steps 28 --guidance 3.5
"""
import argparse
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--lora", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--guidance", type=float, default=3.5)
    a = ap.parse_args()

    import torch
    from diffusers import FluxPipeline

    pipe = FluxPipeline.from_pretrained(a.base, torch_dtype=torch.bfloat16)
    pipe.load_lora_weights(a.lora)
    pipe.enable_model_cpu_offload()  # fit ~24GB Flux on a 24GB L4 at inference

    os.makedirs(a.out, exist_ok=True)
    prompts = [l.strip() for l in open(a.prompts, encoding="utf-8") if l.strip()]
    for i, p in enumerate(prompts):
        img = pipe(p, num_inference_steps=a.steps, guidance_scale=a.guidance,
                   generator=torch.Generator("cpu").manual_seed(42 + i)).images[0]
        img.save(os.path.join(a.out, f"sample_{i:02d}.png"))
        print(f"  rendered {i}: {p[:60]}", flush=True)


if __name__ == "__main__":
    main()
