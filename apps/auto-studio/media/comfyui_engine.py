#!/usr/bin/env python3
"""
comfyui_engine.py — THE single module that talks to ComfyUI over HTTP.

Every ComfyUI API call in the studio (/prompt, /history, /view, /upload/image,
/system_stats) lives here and ONLY here. Callers:

  - media/comfyui_renderer.py  — the pipeline renderer (thin wrappers, same
    public signatures producer.py / films/ have always used)
  - cli/ilyrium_gen.py         — the interactive CLI that runs ON the EC2 box
    (box.ps1 ships this file + model_registry.json alongside it)
  - studio_tools.py            — the edit_image / inpaint_image agent tools

Design constraints (do not regress):
  * Importable on the box with NOTHING but the stdlib + PIL (PIL only for
    make_region_mask, lazily imported). No requests, no boto3.
  * submit_and_wait RAISES on every failure — no empty fallback files, ever.
    The pipeline records a raise as a failed take (producer.render_shot).
  * gen_prompt passes ollama keep_alive:0 — the 23GB L4 cannot hold
    qwen3-coder (~21GB) AND an image model; qwen must release the GPU
    before the render or ComfyUI OOMs.
  * Models are defined in model_registry.json (provider "comfyui"), each with
    either a "recipe" (programmatic graph: txt2img/img2img/inpaint/region) or
    a "workflow" (pre-exported _api.json template with __PROMPT__/__IMAGE__/
    __SEED__ tokens). Adding a model = one registry entry.

lint-no-raw-sdk: allow — this file is the one sanctioned ComfyUI HTTP surface
(consolidation spec docs/plans/2026-07-12-comfyui-consolidation.md); everything
else must go through it.
"""

import json
import os
import time
import uuid
import random
import urllib.parse
import urllib.request
import urllib.error

# Default to the tunnelled localhost endpoint (127.0.0.1, not 'localhost' —
# Windows resolves localhost to IPv6 and breaks the SSH forward). On the box
# itself this is simply the local server.
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
PROMPT_MODEL = os.getenv("ILYRIUM_PROMPT_MODEL", "qwen3-coder:latest")
# Where ComfyUI writes outputs when we DON'T download via /view (i.e. when the
# caller runs on the box itself and wants the box-local path).
OUTPUT_ROOT = os.getenv("COMFYUI_OUTPUT_ROOT", "/home/ubuntu/ComfyUI/output")

DEFAULT_MODEL = "zimage"


class ComfyUIError(RuntimeError):
    """Raised for any ComfyUI submit/poll/download failure."""


# --------------------------------------------------------------------------- #
# Low-level HTTP (stdlib only, so the box venv needs nothing extra)
# --------------------------------------------------------------------------- #
def _post_json(url: str, payload: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _get_json(url: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def is_up(base_url: str = None, timeout: int = 4) -> bool:
    """Reachability probe (GET /system_stats)."""
    base = (base_url or COMFYUI_URL).rstrip("/")
    try:
        with urllib.request.urlopen(base + "/system_stats", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Model registry (model_registry.json is the ONLY place a model is defined)
# --------------------------------------------------------------------------- #
def _registry_candidates():
    env = os.getenv("ILYRIUM_MODEL_REGISTRY")
    here = os.path.dirname(os.path.abspath(__file__))
    return [p for p in (
        env,
        os.path.join(here, "model_registry.json"),                 # box: shipped flat
        os.path.join(os.path.dirname(here), "model_registry.json"),  # repo: media/../
    ) if p]


def _load_registry() -> dict:
    for p in _registry_candidates():
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    raise ComfyUIError(
        "model_registry.json not found (looked at: %s). The registry defines the "
        "ComfyUI models; ship it alongside this file or set ILYRIUM_MODEL_REGISTRY."
        % ", ".join(_registry_candidates()))


def comfyui_models() -> dict:
    """{short_id: registry entry} for every provider=='comfyui' model that has a
    recipe or workflow (the bare capability entry 'comfyui' is skipped)."""
    out = {}
    for m in _load_registry().get("models", []):
        if m.get("provider") != "comfyui":
            continue
        if not (m.get("recipe") or m.get("workflow")):
            continue
        short = m["id"].split(":", 1)[1] if ":" in m["id"] else m["id"]
        out[short] = m
    return out


def available_model_ids() -> list:
    return sorted(comfyui_models())


def load_model(model_id: str) -> dict:
    """Resolve 'zimage' / 'comfyui:zimage' to its registry entry. Raises a clear
    ValueError on unknown ids — never a silent fallback."""
    short = (model_id or DEFAULT_MODEL)
    if short.startswith("comfyui:"):
        short = short.split(":", 1)[1]
    models = comfyui_models()
    if short not in models:
        raise ValueError(
            f"Unknown ComfyUI model '{model_id}'. Known models: "
            f"{', '.join(sorted(models))}. Add new ones as a provider='comfyui' "
            f"entry in model_registry.json (recipe or workflow field).")
    return models[short]


# --------------------------------------------------------------------------- #
# Prompt generation (qwen3-coder via ollama on the box)
# --------------------------------------------------------------------------- #
def gen_prompt(idea: str, hint: str, base: str = None, ollama_url: str = None) -> str:
    """Ask qwen3-coder for an image prompt.

    If `base` (the previous scene's prompt) is given, produce an EDITED
    version of it that applies `idea` as a change — keeping everything
    else the same. Otherwise expand `idea` into a fresh prompt.
    """
    if base:
        instr = (
            "Here is a description of an image:\n"
            f"{base}\n\n"
            f"Produce a NEW description of the SAME image after this change is "
            f"applied: {idea}\n\n"
            "Rules: Describe the resulting scene directly and visually, as if "
            "describing a photo. Keep every unchanged detail (subject, pose, "
            "setting, style, composition). Do NOT mention files, editing, "
            "'modify', 'remove', or that a change was made -- only describe "
            "what is now visible. Output ONE vivid single-line description. "
            "No preamble, quotes, or markdown."
        )
    else:
        instr = (f"Write ONE vivid {hint} text-to-image prompt on a single "
                 f"line for: {idea}. No preamble, no quotes, no markdown. "
                 f"Just the prompt.")
    out = _post_json(f"{(ollama_url or OLLAMA_URL).rstrip('/')}/api/generate",
                     {"model": PROMPT_MODEL, "stream": False,
                      "prompt": instr,
                      # Release qwen3 from the GPU right after it answers so
                      # ComfyUI has the full 23GB to render -- otherwise a
                      # ~21GB qwen + an image model OOMs the L4.
                      "keep_alive": 0},
                     # cold-loading the ~21GB model takes minutes; don't time out
                     timeout=600)
    return " ".join(out["response"].strip().split())


# --------------------------------------------------------------------------- #
# Masks
# --------------------------------------------------------------------------- #
def comfy_input_dir() -> str:
    """ComfyUI's input dir on the box (sibling of the output root)."""
    return os.path.join(os.path.dirname(OUTPUT_ROOT), "input")


def make_region_mask(region: str, w: int, h: int, save_dir: str = None,
                     name: str = "region_mask.png") -> str:
    """Build a white-rectangle-on-black mask PNG from an 'x1,y1,x2,y2' region
    spec. Coords are fractions (0-1) if all <= 1, else pixels. Saves into
    `save_dir` (default: ComfyUI's local input dir — the on-box case) and
    returns the full path. Desktop callers save to a temp dir and upload the
    file with upload_image()."""
    from PIL import Image, ImageDraw
    nums = [float(x) for x in region.split(",")]
    if len(nums) != 4:
        raise ValueError("region must be x1,y1,x2,y2")
    if all(n <= 1.0 for n in nums):
        x1, y1, x2, y2 = (nums[0] * w, nums[1] * h, nums[2] * w, nums[3] * h)
    else:
        x1, y1, x2, y2 = nums
    box = [int(min(x1, x2)), int(min(y1, y2)),
           int(max(x1, x2)), int(max(y1, y2))]
    im = Image.new("RGB", (w, h), (0, 0, 0))
    ImageDraw.Draw(im).rectangle(box, fill=(255, 255, 255))
    target_dir = save_dir or comfy_input_dir()
    if not os.path.isdir(target_dir):
        raise ComfyUIError(
            f"Mask save dir not found: {target_dir}. Off-box callers must pass "
            f"save_dir=<temp dir> and upload the mask via upload_image().")
    path = os.path.join(target_dir, name)
    im.save(path)
    return path


# --------------------------------------------------------------------------- #
# Graph building
# --------------------------------------------------------------------------- #
def inject_tokens(wf_text: str, visual_prompt: str, image_name: str = None,
                  seed: int = None) -> str:
    """JSON-safe replacement of __PROMPT__ (and optionally __IMAGE__) tokens.

    __SEED__ (used bare, not quoted, e.g. "seed": __SEED__) is replaced with an
    integer so renders vary per call. If the workflow contains the token and no
    seed is supplied, a random one is generated."""
    wf_text = wf_text.replace("__PROMPT__", json.dumps(visual_prompt)[1:-1])
    if image_name is not None:
        wf_text = wf_text.replace("__IMAGE__", json.dumps(image_name)[1:-1])
    if "__SEED__" in wf_text:
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
        wf_text = wf_text.replace("__SEED__", str(int(seed)))
    return wf_text


def _resolve_workflow_path(path: str) -> str:
    """Resolve a registry 'workflow' path (relative to apps/auto-studio/)."""
    if os.path.isabs(path) and os.path.exists(path):
        return path
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (os.getcwd(), os.path.dirname(here), here):
        cand = os.path.join(base, path)
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(
        f"ComfyUI workflow template not found: '{path}'. Export it from ComfyUI "
        f"(Save API Format) with __PROMPT__/__SEED__ tokens.")


def build_graph(model_spec, prompt: str, *, seed: int = None,
                width: int = 1024, height: int = 1024,
                img: str = None, mask: str = None, region: str = None,
                denoise: float = 0.65, prefix: str = "ilyrium") -> dict:
    """Return a ComfyUI API-format graph for a registry model.

    model_spec  a model id ('zimage', 'comfyui:flux2', ...) or a registry entry.
    img  set  -> img2img (whole image nudged by denoise); `img` is a filename
                 already in ComfyUI's /input store (see upload_image).
    mask set  -> inpaint: only the white area of the mask changes; the rest of
                 `img` is preserved pixel-for-pixel (needs img too).
    region set-> like mask, but builds a rectangular mask from 'x1,y1,x2,y2'
                 on the fly (needs a local ComfyUI input dir — the on-box case;
                 off-box callers build + upload the mask themselves).
    neither   -> text-to-image.
    """
    entry = load_model(model_spec) if isinstance(model_spec, str) else model_spec
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    # (b) template workflow: token-inject a pre-exported _api.json graph.
    if entry.get("workflow") and not entry.get("recipe"):
        if img or mask or region:
            raise ValueError(
                f"Model '{entry.get('id')}' is template-based ('workflow'); "
                f"img2img/inpaint need a 'recipe' model.")
        with open(_resolve_workflow_path(entry["workflow"]), encoding="utf-8") as f:
            return json.loads(inject_tokens(f.read(), prompt, seed=seed))

    # (a) programmatic recipe graph (txt2img / img2img / inpaint / region).
    m = entry.get("recipe") if isinstance(entry, dict) and entry.get("recipe") else entry
    if region and img and not mask:
        mask = os.path.basename(make_region_mask(region, width, height))

    wf = {
        "1": {"inputs": {"unet_name": m["unet"],
                         "weight_dtype": m.get("weight_dtype", "default")},
              "class_type": "UNETLoader"},
        "2": {"inputs": {"clip_name": m["clip"], "type": m["clip_type"]},
              "class_type": "CLIPLoader"},
        "3": {"inputs": {"vae_name": m["vae"]}, "class_type": "VAELoader"},
        "4": {"inputs": {"text": prompt, "clip": ["2", 0]},
              "class_type": "CLIPTextEncode"},
        "5": {"inputs": {"text": "", "clip": ["2", 0]},
              "class_type": "CLIPTextEncode"},
        "7": {"inputs": {"seed": seed, "steps": m["steps"], "cfg": m["cfg"],
                         "sampler_name": m["sampler"],
                         "scheduler": m["scheduler"], "denoise": denoise,
                         "model": ["1", 0], "positive": ["4", 0],
                         "negative": ["5", 0], "latent_image": ["6", 0]},
              "class_type": "KSampler"},
        "8": {"inputs": {"samples": ["7", 0], "vae": ["3", 0]},
              "class_type": "VAEDecode"},
        "9": {"inputs": {"filename_prefix": prefix, "images": ["8", 0]},
              "class_type": "SaveImage"},
    }
    if img and mask:
        # inpaint: load image + mask, scale both, VAEEncodeForInpaint builds a
        # masked latent; only the masked pixels get denoised.
        wf["10"] = {"inputs": {"image": img, "upload": "image"},
                    "class_type": "LoadImage"}
        wf["11"] = {"inputs": {"upscale_method": "lanczos", "width": width,
                               "height": height, "crop": "center",
                               "image": ["10", 0]},
                    "class_type": "ImageScale"}
        wf["12"] = {"inputs": {"image": mask, "channel": "red",
                               "upload": "image"},
                    "class_type": "LoadImageMask"}
        wf["6"] = {"inputs": {"pixels": ["11", 0], "vae": ["3", 0],
                              "mask": ["12", 0], "grow_mask_by": 6},
                   "class_type": "VAEEncodeForInpaint"}
        # full denoise inside the mask for a real change; mask limits the area.
        wf["7"]["inputs"]["denoise"] = 1.0
    elif img:
        # img2img: load the uploaded reference, scale to target, VAE-encode
        # it into the init latent (node 6).
        wf["10"] = {"inputs": {"image": img, "upload": "image"},
                    "class_type": "LoadImage"}
        wf["11"] = {"inputs": {"upscale_method": "lanczos", "width": width,
                               "height": height, "crop": "center",
                               "image": ["10", 0]},
                    "class_type": "ImageScale"}
        wf["6"] = {"inputs": {"pixels": ["11", 0], "vae": ["3", 0]},
                   "class_type": "VAEEncode"}
    else:
        wf["6"] = {"inputs": {"width": width, "height": height, "batch_size": 1},
                   "class_type": m["latent"]}
    return wf


# --------------------------------------------------------------------------- #
# Upload / submit / poll / download
# --------------------------------------------------------------------------- #
def upload_image(path: str, base_url: str = None) -> str:
    """Upload an image to ComfyUI's input store (/upload/image); return the
    stored name (prefixed with its subfolder when ComfyUI nests it). Raises."""
    base = (base_url or COMFYUI_URL).rstrip("/")
    if not os.path.exists(path):
        raise ComfyUIError(f"Image to upload not found: {path}")
    with open(path, "rb") as fh:
        data = fh.read()
    boundary = "----ilyrium" + uuid.uuid4().hex
    fname = os.path.basename(path)
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="image"; filename="{fname}"\r\n'.encode(),
        b"Content-Type: application/octet-stream\r\n\r\n",
        data, b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
        f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        base + "/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            info = json.load(r)  # {"name": "...", "subfolder": "", "type": "input"}
    except urllib.error.HTTPError as e:
        raise ComfyUIError(f"Image upload failed: HTTP {e.code} {e.read()[:300]!r}") from e
    name = info["name"]
    sub = info.get("subfolder")
    return f"{sub}/{name}" if sub else name


def _first_output_file(outputs: dict):
    """Find the produced file, preferring video (gifs/videos) across ALL nodes
    before falling back to a still image."""
    for key in ("gifs", "videos", "images"):
        for node_out in outputs.values():
            files = node_out.get(key)
            if files:
                return files[0]  # {filename, subfolder, type}
    return None


def submit_and_wait(graph: dict, base_url: str = None, timeout: int = 600, *,
                    output_dir: str = None, output_name: str = None,
                    poll_interval: float = 2.0) -> str:
    """Submit a graph, poll /history until done, return the produced file path.

    output_dir set   -> download via /view and save locally (desktop/pipeline);
                        output_name may omit the extension — the produced one is
                        used (and a wrong extension is corrected to match).
    output_dir unset -> return the ComfyUI-local output path (the on-box case).

    RAISES ComfyUIError on every failure — no fallback files.
    """
    base = (base_url or COMFYUI_URL).rstrip("/")
    if not is_up(base):
        raise ComfyUIError(
            f"ComfyUI is unreachable at {base}. Start the EC2 GPU box and the "
            f"tunnel (cli/box.ps1 start + tunnel) so :8188 answers.")

    client_id = str(uuid.uuid4())
    try:
        resp = _post_json(base + "/prompt", {"prompt": graph, "client_id": client_id},
                          timeout=60)
    except urllib.error.HTTPError as e:
        raise ComfyUIError(
            f"ComfyUI rejected the workflow: HTTP {e.code} {e.read()[:500]!r}") from e
    prompt_id = resp["prompt_id"]

    deadline = time.time() + timeout
    file_info = None
    while time.time() < deadline:
        try:
            hist = _get_json(f"{base}/history/{prompt_id}", timeout=15)
        except Exception:
            time.sleep(poll_interval)
            continue
        if prompt_id in hist:
            entry = hist[prompt_id]
            status = entry.get("status") or {}
            if status.get("status_str") == "error":
                msgs = [m for m in status.get("messages", []) if m and m[0] == "execution_error"]
                detail = json.dumps(msgs[0][1], default=str)[:500] if msgs else "see ComfyUI log"
                raise ComfyUIError(f"ComfyUI execution failed (prompt {prompt_id}): {detail}")
            outputs = entry.get("outputs")
            if outputs:
                file_info = _first_output_file(outputs)
                break
            if status.get("completed"):
                raise ComfyUIError(
                    f"ComfyUI completed but produced no outputs (prompt_id={prompt_id}).")
        time.sleep(poll_interval)
    else:
        raise ComfyUIError(f"ComfyUI render timed out after {timeout}s (prompt_id={prompt_id}).")

    if not file_info:
        raise ComfyUIError(f"ComfyUI produced no output file (prompt_id={prompt_id}).")

    if output_dir is None:
        return os.path.join(OUTPUT_ROOT, file_info.get("subfolder", ""),
                            file_info["filename"])

    params = urllib.parse.urlencode({
        "filename": file_info["filename"],
        "subfolder": file_info.get("subfolder", ""),
        "type": file_info.get("type", "output"),
    })
    try:
        with urllib.request.urlopen(f"{base}/view?{params}", timeout=300) as r:
            content = r.read()
    except urllib.error.HTTPError as e:
        raise ComfyUIError(f"Failed to download rendered file: HTTP {e.code}") from e

    os.makedirs(output_dir, exist_ok=True)
    produced_ext = os.path.splitext(file_info["filename"])[1] or ".png"
    name = output_name or f"comfyui_{prompt_id[:8]}{produced_ext}"
    stem, ext = os.path.splitext(name)
    if ext.lower() != produced_ext.lower():
        # never lie about the payload: a still stays .png even if a video
        # filename was requested (and vice versa).
        name = stem + produced_ext
    out = os.path.join(output_dir, name)
    with open(out, "wb") as f:
        f.write(content)
    return out
