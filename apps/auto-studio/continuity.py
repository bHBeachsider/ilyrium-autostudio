#!/usr/bin/env python3
"""
continuity.py — resolve a character's continuity assets into a concrete ComfyUI render plan.

The single source of truth for "how do I render THIS character on-model?". It composes what
already exists in a project — a registered character LoRA (lora_library.json), uploaded/curated
reference stills — and returns a plan the asset_gen stage feeds straight into render_shot →
render_scene_comfyui (img2img + LoRA) → render_i2v_comfyui (Wan 2.2 still→video).

Design (see docs/superpowers/specs/continuity design): render is ALWAYS on-box ComfyUI — no grok,
no cloud. Precedence for the still step:
  1. registered, usable LoRA + a reference still -> flux_lora_img2img (LoRA locks identity)
  2. a reference still only                       -> <model>_img2img (ref nudges the look)
  3. neither                                      -> method='none' (caller decides: block, or
                                                      fall back to plain txt2img)

A "plan" is a dict:
  { "method": "lora_img2img" | "img2img" | "none",
    "still_model": "comfyui:flux2" | "comfyui:zimage" | ...,   # which on-box still model
    "still_workflow": "<abs path to a *_api.json template>" | None,
    "anchor": "<abs path to the best reference still>" | None,
    "lora_name": "<safetensors filename on the box>" | None,
    "i2v_workflow": "<abs path to wan22_i2v_api.json>",         # still -> video
    "why": ["human-readable reasons"] }
"""
import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
WORKFLOWS = os.path.join(HERE, "comfyui_workflows")

# Reference stills we accept as an anchor, best-first by convention (front is the strongest lock).
_ANCHOR_PREFERENCE = ("front", "threequarter", "3q", "portrait", "side", "rear", "back")
_IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")

# A registered LoRA is usable for rendering once it has a filename + a "trained/ready" status.
_USABLE_LORA_STATUS = {"trained", "ready", "local", "registered", "done"}


def _project_dir(project):
    """Accept a project dir path OR a project name and return its directory."""
    if os.path.isdir(str(project)):
        return project
    from project_paths import resolve_project
    return resolve_project(project)


def _char_slug(character):
    """Normalize a character identifier to a folder-safe slug (Stripe -> stripe)."""
    return "".join(c for c in str(character or "").lower().strip() if c.isalnum() or c in "_-")


def _load_lora_library(project_dir):
    """Return the loras[] list from the project's lora_library.json (empty on any miss)."""
    lib = os.path.join(project_dir, "03_design", "characters", "loras", "lora_library.json")
    try:
        return json.load(open(lib, encoding="utf-8")).get("loras", [])
    except Exception:
        return []


def _find_lora(project_dir, character):
    """The best usable LoRA for `character`: a lora_library entry whose name/trigger matches
    and whose status is trained/ready. Returns its safetensors filename or None."""
    slug = _char_slug(character)
    for lo in _load_lora_library(project_dir):
        name = _char_slug(lo.get("name")) or _char_slug(lo.get("trigger_word"))
        fn = lo.get("filename")
        status = str(lo.get("status", "")).lower()
        if fn and slug and slug in (name or "") and status in _USABLE_LORA_STATUS:
            return fn
    return None


def _find_anchor(project_dir, character):
    """The best reference still for `character`. Searches, in order:
      1. the Stage-1 bible character _media uploads,
      2. the curated anchors/ set,
      3. source_refs/good.
    Returns an absolute path (front-ish preferred) or None."""
    slug = _char_slug(character)
    search_dirs = [
        os.path.join(project_dir, "01_development", "bible", "characters", "_media"),
        os.path.join(project_dir, "03_design", "characters", "anchors"),
        os.path.join(project_dir, "03_design", "characters", slug, "source_refs", "good"),
        os.path.join(project_dir, "03_design", "characters", "anchors", slug),
    ]
    candidates = []
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            p = os.path.join(d, fn)
            if os.path.isfile(p) and fn.lower().endswith(_IMG_EXT):
                candidates.append(p)
    if not candidates:
        return None

    def rank(path):
        base = os.path.basename(path).lower()
        # Prefer a filename that names this character AND a strong viewing angle.
        names_char = 1 if slug and slug in base else 0
        angle = next((i for i, a in enumerate(_ANCHOR_PREFERENCE) if a in base), len(_ANCHOR_PREFERENCE))
        return (-names_char, angle, base)   # char-named first, then front→rear, then stable

    candidates.sort(key=rank)
    return os.path.abspath(candidates[0])


def _still_model(project_dir):
    """Pick the on-box still model. Uses model_select against the project kernel when possible,
    restricted to comfyui models; falls back to comfyui:flux2 (the reference-friendly default)."""
    try:
        import model_select
        kf = os.path.join(project_dir, "style_kernel.json")
        kernel = json.load(open(kf, encoding="utf-8")) if os.path.exists(kf) else {}
        ranked = model_select.recommend(kernel, need="txt2img")
        for m in ranked:
            mid = m.get("id", "")
            if mid.startswith("comfyui") and m.get("available", True):
                return mid
    except Exception:
        pass
    return "comfyui:flux2"


def _wf(name):
    p = os.path.join(WORKFLOWS, name)
    return p if os.path.exists(p) else None


def resolve(project, character):
    """Resolve a character's continuity render plan. `project` is a dir path or project name.

    Never raises for a missing asset — returns method='none' so the caller decides what to do
    (block, or render a plain txt2img). Raises only if the project itself can't be resolved."""
    project_dir = _project_dir(project)
    anchor = _find_anchor(project_dir, character)
    lora = _find_lora(project_dir, character)
    still_model = _still_model(project_dir)
    i2v = _wf("wan22_i2v_api.json")
    why = []

    if lora and anchor:
        why.append(f"LoRA {lora} + reference {os.path.basename(anchor)} → identity-locked img2img")
        return {"method": "lora_img2img", "still_model": still_model,
                "still_workflow": _wf("flux_lora_img2img_api.json"),
                "anchor": anchor, "lora_name": lora, "i2v_workflow": i2v, "why": why}

    if anchor:
        # Match the img2img template to the chosen still model. Bare 'comfyui' (the default
        # registry model) and 'comfyui:flux2' both use the flux img2img template.
        tmpl = {"comfyui:zimage": "zimage_img2img_api.json"}.get(still_model, "flux_img2img_api.json")
        why.append(f"reference {os.path.basename(anchor)} → {still_model} img2img (no registered LoRA)")
        return {"method": "img2img", "still_model": still_model,
                "still_workflow": _wf(tmpl),
                "anchor": anchor, "lora_name": None, "i2v_workflow": i2v, "why": why}

    why.append("no continuity asset (no LoRA, no reference still) for this character")
    return {"method": "none", "still_model": still_model, "still_workflow": None,
            "anchor": None, "lora_name": None, "i2v_workflow": i2v, "why": why}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Resolve a character's continuity render plan.")
    ap.add_argument("project")
    ap.add_argument("character")
    a = ap.parse_args()
    print(json.dumps(resolve(a.project, a.character), indent=2))


if __name__ == "__main__":
    main()
