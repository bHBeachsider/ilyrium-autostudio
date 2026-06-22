"""
ComfyUI renderer — the self-hosted, controllable generation engine.

Runs one of YOUR exported ComfyUI workflows (the node graph) on the GPU box,
injecting the shot's prompt, then downloads the produced clip. Mirrors the
other renderers' contract: returns the saved file path, raises on failure.

Prompt injection: put the literal token  __PROMPT__  in the positive-prompt
text of your workflow, export it via ComfyUI's "Save (API Format)", and point
COMFYUI_WORKFLOW at that file. The token is replaced with the shot's prompt.

For image-to-video (Wan 2.2 i2v) the workflow also needs a start frame: put the
literal token  __IMAGE__  in the LoadImage node's "image" field. render_i2v_comfyui
uploads the still to ComfyUI's input store and injects the stored filename.

For shot rendering the workflow should OUTPUT A VIDEO (AnimateDiff / SVD / WAN
via VHS_VideoCombine -> mp4). A still-image workflow will return a .png, which
is fine for reference frames but won't stitch into the cut as a clip.

Config via env:
  COMFYUI_URL          default http://127.0.0.1:8188  (through the SSH tunnel)
  COMFYUI_WORKFLOW     default comfyui_workflows/default_api.json    (text-to-video)
  COMFYUI_I2V_WORKFLOW default comfyui_workflows/wan22_i2v_api.json  (image-to-video)
"""

import os
import json
import time
import uuid

from ec2_session import COMFYUI_URL, is_comfyui_up


def _first_output_file(outputs: dict):
    """Find the produced file, preferring video (gifs/videos) across ALL nodes
    before falling back to a still image."""
    for key in ("gifs", "videos", "images"):
        for node_out in outputs.values():
            files = node_out.get(key)
            if files:
                return files[0]  # {filename, subfolder, type}
    return None


def _inject_tokens(wf_text: str, visual_prompt: str, image_name: str = None) -> str:
    """JSON-safe replacement of __PROMPT__ (and optionally __IMAGE__) tokens."""
    wf_text = wf_text.replace("__PROMPT__", json.dumps(visual_prompt)[1:-1])
    if image_name is not None:
        wf_text = wf_text.replace("__IMAGE__", json.dumps(image_name)[1:-1])
    return wf_text


def _run_workflow(workflow: dict, scene_number: int, base: str, output_dir: str,
                  output_name: str, timeout: int) -> str:
    """Submit a parsed workflow, poll history until done, download the produced file.
    Shared by both the text-to-video and image-to-video render paths."""
    import requests
    client_id = str(uuid.uuid4())
    resp = requests.post(base + "/prompt", json={"prompt": workflow, "client_id": client_id}, timeout=30)
    resp.raise_for_status()
    prompt_id = resp.json()["prompt_id"]

    # Poll history until this prompt completes.
    deadline = time.time() + timeout
    outputs = None
    while time.time() < deadline:
        hist = requests.get(f"{base}/history/{prompt_id}", timeout=15).json()
        if prompt_id in hist:
            outputs = hist[prompt_id].get("outputs")
            break
        time.sleep(2)
    if not outputs:
        raise RuntimeError(f"ComfyUI render timed out after {timeout}s for scene {scene_number}.")

    file_info = _first_output_file(outputs)
    if not file_info:
        raise RuntimeError(f"ComfyUI produced no output file for scene {scene_number}.")

    params = {
        "filename": file_info["filename"],
        "subfolder": file_info.get("subfolder", ""),
        "type": file_info.get("type", "output"),
    }
    data = requests.get(base + "/view", params=params, timeout=300)
    data.raise_for_status()

    os.makedirs(output_dir, exist_ok=True)
    ext = os.path.splitext(file_info["filename"])[1] or ".mp4"
    out = os.path.join(output_dir, output_name or f"scene_{scene_number}{ext}")
    with open(out, "wb") as f:
        f.write(data.content)

    print(f"✅ [COMFYUI] Scene {scene_number} saved as {out}")
    return out


def upload_comfyui_image(image_path: str, base: str) -> str:
    """Upload a start frame to ComfyUI's input store; return the stored filename
    (prefixed with its subfolder when ComfyUI nests it)."""
    import requests
    with open(image_path, "rb") as fh:
        files = {
            "image": (os.path.basename(image_path), fh, "image/png"),
            "overwrite": (None, "true"),
        }
        r = requests.post(base + "/upload/image", files=files, timeout=60)
    r.raise_for_status()
    info = r.json()  # {"name": "...", "subfolder": "", "type": "input"}
    name = info["name"]
    sub = info.get("subfolder")
    return f"{sub}/{name}" if sub else name


def render_scene_comfyui(visual_prompt: str, scene_number: int, output_dir: str = ".",
                         output_name: str = None, workflow_path: str = None,
                         url: str = None, timeout: int = 600) -> str:
    base = (url or COMFYUI_URL).rstrip("/")
    if not is_comfyui_up(base):
        raise RuntimeError(
            f"ComfyUI is not reachable at {base}. Start the EC2 GPU + open the tunnel "
            f"(your ilyrium-ec2-session) and make sure ComfyUI is listening on 8188."
        )

    wf_path = workflow_path or os.getenv("COMFYUI_WORKFLOW", "comfyui_workflows/default_api.json")
    if not os.path.exists(wf_path):
        raise RuntimeError(
            f"ComfyUI workflow not found at '{wf_path}'. Export one from ComfyUI via "
            f"'Save (API Format)', put __PROMPT__ in its positive prompt, and set COMFYUI_WORKFLOW."
        )

    with open(wf_path, "r", encoding="utf-8") as f:
        wf_text = f.read()
    workflow = json.loads(_inject_tokens(wf_text, visual_prompt))

    print(f"\n🎨 [COMFYUI] Scene {scene_number}: submitting workflow to {base}…")
    return _run_workflow(workflow, scene_number, base, output_dir, output_name, timeout)


def render_i2v_comfyui(image_path: str, visual_prompt: str, scene_number: int,
                       output_dir: str = ".", output_name: str = None,
                       workflow_path: str = None, url: str = None, timeout: int = 1200) -> str:
    """Wan 2.2 image-to-video: upload `image_path` as the start frame, inject the
    motion prompt, run the workflow, return the saved clip path."""
    if not os.path.exists(image_path):
        raise RuntimeError(f"Start image not found: {image_path}")
    base = (url or COMFYUI_URL).rstrip("/")
    if not is_comfyui_up(base):
        raise RuntimeError(
            f"ComfyUI is not reachable at {base}. Start the EC2 GPU + open the tunnel "
            f"(ilyrium-ec2-session) and make sure ComfyUI is listening on 8188."
        )
    wf_path = workflow_path or os.getenv("COMFYUI_I2V_WORKFLOW", "comfyui_workflows/wan22_i2v_api.json")
    if not os.path.exists(wf_path):
        raise RuntimeError(
            f"Wan i2v workflow not found at '{wf_path}'. Export it from ComfyUI (Save API Format), "
            f"put __PROMPT__ in the positive CLIPTextEncode and __IMAGE__ in the LoadImage 'image' field."
        )
    image_name = upload_comfyui_image(image_path, base)
    with open(wf_path, "r", encoding="utf-8") as f:
        wf_text = f.read()
    workflow = json.loads(_inject_tokens(wf_text, visual_prompt, image_name))
    print(f"\n🎨 [COMFYUI-i2v] Scene {scene_number}: {os.path.basename(image_path)} → video on {base}…")
    return _run_workflow(workflow, scene_number, base, output_dir, output_name, timeout)
