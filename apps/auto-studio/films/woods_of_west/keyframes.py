"""Per-shot keyframe stills via Fal nano-banana edit, style- and character-locked.
The still is the Wan i2v start frame — the cross-shot consistency mechanism."""

import os
from media.fal_image_edit import edit_image_fal
from films.woods_of_west import script


def _edit_with_timeout(prompt, refs, out_path, timeout):
    """Run the Fal edit with a hard wall-clock timeout (daemon thread, Windows-safe).
    A hung Fal request raises TimeoutError so the caller skips the shot instead of
    blocking the whole render — this was the root cause of a 7-hour stall."""
    import threading
    box = {}

    def _run():
        try:
            box["result"] = edit_image_fal(prompt, refs, out_path, resolution="2K", aspect_ratio="16:9")
        except Exception as e:  # carry the real error back to the caller
            box["error"] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError(f"Fal keyframe edit exceeded {timeout}s (hung) for {out_path}")
    if "error" in box:
        raise box["error"]
    return box["result"]


def compose_keyframe_prompt(shot: dict, style: str) -> str:
    looks = "; ".join(script.CHARACTERS[c] for c in shot.get("characters", []))
    parts = [script.style_prefix(style), "16:9", shot["visual"]]
    if looks:
        parts.append(f"characters on-model — {looks}")
    return ", ".join(parts)


def generate_shot_keyframe(shot: dict, style: str, char_refs: dict, out_dir: str) -> str:
    """Edit a style+character-locked still for `shot` from the relevant character
    reference sheets, save it, and return the path. Establishing shots (no character
    in frame) seed from the first available sheet so the style stays consistent."""
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"shot{shot['id']}_keyframe.png")
    if os.path.exists(out_path):
        return out_path  # reuse an existing keyframe — consistency + fewer Fal calls
    prompt = compose_keyframe_prompt(shot, style)
    refs = [char_refs[c] for c in shot.get("characters", []) if c in char_refs]
    if not refs:
        refs = [next(iter(char_refs.values()))] if char_refs else None
    if not refs:
        raise RuntimeError(f"shot {shot['id']}: no character refs available to seed the keyframe edit")
    timeout = int(os.getenv("FAL_KEYFRAME_TIMEOUT", "180"))
    saved = _edit_with_timeout(prompt, refs, out_path, timeout)
    return saved[0] if isinstance(saved, list) else saved
