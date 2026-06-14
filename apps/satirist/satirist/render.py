"""GPU render: SDXL base + Nast Hand LoRA via diffusers. Runs on a CUDA box only.
Heavy imports are lazy so this module imports on machines without torch/diffusers."""
import os
import subprocess

from . import config


def compose_prompt(image_prompt: str, *, style_block: str, avatar_desc: str = None,
                   trigger: str = None) -> str:
    """Build the final render prompt: PREPEND the descriptive style block (and, for
    character panels, the avatar description) ahead of the brain's raw image_prompt.

    On Flux/SDXL a *described* style is load-bearing while a bare trigger token is not
    (validated 2026-06-14 on the Broderick hands: bare `brdrck`/`brdmc` produced generic
    cartoon/photoreal, but the same LoRAs rendered strong Broderick ink once the style —
    and, for characters, the avatar — was described). So the style leads the prompt and
    `trigger` is only a harmless tail for the LoRA's trained token. Empty parts are skipped.
    """
    parts = [p.strip() for p in (style_block, avatar_desc, image_prompt) if p and p.strip()]
    composed = ", ".join(parts)
    if trigger and trigger.strip():
        composed = f"{composed}, {trigger.strip()}" if composed else trigger.strip()
    return composed


def fetch_lora(s3_uri: str = None, dest: str = None) -> str:
    """Download the LoRA safetensors from S3 to `dest` (skips if already present). Returns dest."""
    s3_uri = s3_uri or config.LORA_S3_URI
    dest = dest or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "var",
                                "nast_sdxl.safetensors")
    dest = os.path.abspath(dest)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    subprocess.run(["aws", "s3", "cp", s3_uri, dest, "--only-show-errors"], check=True)
    return dest


def render_sdxl(image_prompt: str, out_path: str, lora_path: str = None,
                steps: int = 30, guidance: float = 6.0, seed: int = 0) -> str:
    """Load SDXL + the Nast LoRA, generate one image from image_prompt, save to out_path. GPU only."""
    import torch
    from diffusers import StableDiffusionXLPipeline

    lora_path = lora_path or fetch_lora()
    pipe = StableDiffusionXLPipeline.from_pretrained(
        config.SDXL_BASE, torch_dtype=torch.float16, use_safetensors=True).to("cuda")
    pipe.load_lora_weights(lora_path)
    gen = torch.Generator(device="cuda").manual_seed(seed)
    image = pipe(prompt=image_prompt, num_inference_steps=steps,
                 guidance_scale=guidance, generator=gen).images[0]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    image.save(out_path)
    return out_path
