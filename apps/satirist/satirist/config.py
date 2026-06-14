"""Paths and provider defaults for the satirist creative loop. Override via env."""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_VAR = os.path.join(os.path.dirname(_HERE), "var")  # apps/satirist/var

# intake-spine SQLite store the RAG step reads from
DB_PATH = os.environ.get("INTAKE_DB", os.path.join(_VAR, "intake.db"))
# where finished cartoons + sidecar JSON land
OUT_DIR = os.environ.get("SATIRIST_OUT", os.path.join(_VAR, "output"))

# Nast Brain (Ollama). Host configurable; model name is fixed by the deploy.
BRAIN_URL = os.environ.get("BRAIN_URL", "http://localhost:11434")
BRAIN_MODEL = os.environ.get("BRAIN_MODEL", "nast-brain")

# Taste judge (OpenRouter)
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "anthropic/claude-sonnet-4.6")
JUDGE_THRESHOLD = float(os.environ.get("JUDGE_THRESHOLD", "3.5"))

# SDXL Hand LoRA (GPU render step)
LORA_S3_URI = os.environ.get(
    "NAST_LORA_S3", "s3://ilyrium-slm-foundry/models/nast/hand/sdxl/nast_sdxl.safetensors")
SDXL_BASE = os.environ.get("SDXL_BASE", "stabilityai/stable-diffusion-xl-base-1.0")
STYLE_TRIGGER = os.environ.get("NAST_STYLE_TRIGGER", "thomas_nast_style")

# Descriptive style block PREPENDED to every render. On Flux/SDXL a described style is
# load-bearing; a bare trigger is not (validated 2026-06-14). Override via env, or load a
# persona's block from its style_kernel.json "look" field via load_style_block().
STYLE_BLOCK = os.environ.get(
    "SATIRIST_STYLE_BLOCK",
    "black and white 19th-century wood engraving, dense cross-hatching, "
    "Harper's Weekly editorial cartoon style, heavy ink")
# Recurring-character avatar description, injected only for character panels (empty = off).
# e.g. Broderick: "a heavyset bald man with a full gray beard and thick black rectangular glasses".
AVATAR_DESC = os.environ.get("SATIRIST_AVATAR_DESC", "")


def load_style_block(kernel_path: str) -> str:
    """Return the 'look' string from a persona style_kernel.json (the documented style-block source)."""
    import json
    with open(kernel_path, encoding="utf-8") as f:
        return json.load(f).get("look", "")


# ---- Flux render backend (Broderick hand). SDXL (Nast) stays the default. ----
RENDER_BACKEND = os.environ.get("SATIRIST_RENDER_BACKEND", "sdxl")  # "sdxl" | "flux"
FLUX_BASE = os.environ.get("FLUX_BASE", "black-forest-labs/FLUX.1-dev")
# Broderick hands (the only trained Flux LoRAs). scales match lora_library.json (brdrck/brdmc).
FLUX_STYLE_LORA_S3 = os.environ.get(
    "FLUX_STYLE_LORA_S3",
    "s3://ilyrium-slm-foundry/models/broderick/hand/flux_v2/broderick_flux_v2.safetensors")
FLUX_CHAR_LORA_S3 = os.environ.get(
    "FLUX_CHAR_LORA_S3",
    "s3://ilyrium-slm-foundry/models/broderick/hand/char/broderick_char.safetensors")
FLUX_STYLE_SCALE = float(os.environ.get("FLUX_STYLE_SCALE", "0.85"))
FLUX_CHAR_SCALE = float(os.environ.get("FLUX_CHAR_SCALE", "0.9"))
