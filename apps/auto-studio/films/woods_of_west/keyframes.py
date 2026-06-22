"""Per-shot keyframe stills via Fal nano-banana edit, style- and character-locked.
The still is the Wan i2v start frame — the cross-shot consistency mechanism."""

import os
from media.fal_image_edit import edit_image_fal
from films.woods_of_west import script


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
    prompt = compose_keyframe_prompt(shot, style)
    refs = [char_refs[c] for c in shot.get("characters", []) if c in char_refs]
    if not refs:
        refs = [next(iter(char_refs.values()))] if char_refs else None
    if not refs:
        raise RuntimeError(f"shot {shot['id']}: no character refs available to seed the keyframe edit")
    saved = edit_image_fal(prompt, refs, out_path, resolution="2K", aspect_ratio="16:9")
    return saved[0] if isinstance(saved, list) else saved
