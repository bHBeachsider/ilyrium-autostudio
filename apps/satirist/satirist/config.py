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
