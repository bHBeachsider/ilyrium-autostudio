"""
ComfyUI renderer — the pipeline's entry points to the self-hosted engine.

THIN WRAPPERS over media/comfyui_engine.py (the single module that owns all
ComfyUI HTTP). Mirrors the other renderers' contract: returns the saved file
path, RAISES on failure. There are NO fallback files any more — a failed
render raises, and producer.render_shot records the take as failed.

Two ways to pick what renders:

  model=...           a registry model id ('zimage', 'flux2',
                      'flux2-klein-9b-uncensored', or 'comfyui:<id>') — the
                      engine builds the graph from model_registry.json.
                      This is what producer.py's 'comfyui:<id>' dispatch uses.
  workflow_path=...   a pre-exported API-format workflow with the literal
                      tokens __PROMPT__ / __SEED__ (and __IMAGE__ for i2v) —
                      the legacy template path, still honoured (also via the
                      COMFYUI_WORKFLOW / COMFYUI_I2V_WORKFLOW env vars).

Neither given -> the default registry model ('zimage'), unless
COMFYUI_WORKFLOW is set (legacy behaviour preserved).

Config via env:
  COMFYUI_URL          default http://127.0.0.1:8188  (through the SSH tunnel)
  COMFYUI_WORKFLOW     optional legacy default template (text-to-image/video)
  COMFYUI_I2V_WORKFLOW default comfyui_workflows/wan22_i2v_api.json (i2v)
"""

import os
import json

from ec2_session import COMFYUI_URL
from .comfyui_engine import (
    ComfyUIError,
    build_graph,
    inject_tokens,
    submit_and_wait,
    upload_image,
    DEFAULT_MODEL,
)

# Kept under its old private name — tests and older callers use it.
_inject_tokens = inject_tokens

__all__ = ["ComfyUIError", "render_scene_comfyui", "render_i2v_comfyui",
           "upload_comfyui_image"]


def _log(msg: str):
    """Print progress without ever masking a real error: legacy cp1252 consoles
    can't encode the emoji, and a UnicodeEncodeError must not replace the
    ComfyUIError the caller actually needs."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def upload_comfyui_image(image_path: str, base: str) -> str:
    """Upload a start frame to ComfyUI's input store; return the stored filename
    (prefixed with its subfolder when ComfyUI nests it). Raises on failure."""
    return upload_image(image_path, base)


def render_scene_comfyui(visual_prompt: str, scene_number: int, output_dir: str = ".",
                         output_name: str = None, workflow_path: str = None,
                         url: str = None, timeout: int = 600, seed: int = None,
                         model: str = None, width: int = 1024, height: int = 1024) -> str:
    """Render one shot on ComfyUI and return the saved local file path.

    model = a registry model id (e.g. 'zimage', 'flux2') OR
    workflow_path = a token-template _api.json. Raises on any failure."""
    base = (url or COMFYUI_URL).rstrip("/")

    if workflow_path is None and model is None:
        workflow_path = os.getenv("COMFYUI_WORKFLOW") or None
    if workflow_path:
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(
                f"ComfyUI workflow not found at '{workflow_path}'. Export one from "
                f"ComfyUI via 'Save (API Format)', put __PROMPT__ in its positive "
                f"prompt, and set COMFYUI_WORKFLOW or pass workflow_path.")
        with open(workflow_path, "r", encoding="utf-8") as f:
            graph = json.loads(inject_tokens(f.read(), visual_prompt, seed=seed))
    else:
        graph = build_graph(model or DEFAULT_MODEL, visual_prompt, seed=seed,
                            width=width, height=height,
                            prefix=f"pipeline/scene_{scene_number}")

    _log(f"\n🎨 [COMFYUI] Scene {scene_number}: submitting workflow to {base}…")
    out = submit_and_wait(graph, base, timeout, output_dir=output_dir,
                          output_name=output_name or f"scene_{scene_number}")
    _log(f"✅ [COMFYUI] Scene {scene_number} saved as {out}")
    return out


def render_i2v_comfyui(image_path: str, visual_prompt: str, scene_number: int,
                       output_dir: str = ".", output_name: str = None,
                       workflow_path: str = None, url: str = None, timeout: int = 1200) -> str:
    """Wan 2.2 image-to-video: upload `image_path` as the start frame, inject the
    motion prompt, run the workflow, return the saved clip path. Raises on failure."""
    if not os.path.exists(image_path):
        raise RuntimeError(f"Start image not found: {image_path}")

    base = (url or COMFYUI_URL).rstrip("/")
    wf_path = workflow_path or os.getenv("COMFYUI_I2V_WORKFLOW",
                                         "comfyui_workflows/wan22_i2v_api.json")
    if not os.path.exists(wf_path):
        raise FileNotFoundError(
            f"Wan i2v workflow not found at '{wf_path}'. Export it from ComfyUI "
            f"(Save API Format), put __PROMPT__ in the positive CLIPTextEncode and "
            f"__IMAGE__ in the LoadImage 'image' field.")

    image_name = upload_comfyui_image(image_path, base)
    with open(wf_path, "r", encoding="utf-8") as f:
        graph = json.loads(inject_tokens(f.read(), visual_prompt, image_name))

    _log(f"\n🎨 [COMFYUI-i2v] Scene {scene_number}: {os.path.basename(image_path)} → video on {base}…")
    out = submit_and_wait(graph, base, timeout, output_dir=output_dir,
                          output_name=output_name or f"scene_{scene_number}")
    _log(f"✅ [COMFYUI-i2v] Scene {scene_number} saved as {out}")
    return out
