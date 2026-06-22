"""Generate the three character reference sheets in a given style (one PNG each).
These refs lock faces/wardrobe across every keyframe (which are edits seeded from
these sheets). Sheets are text-to-image: the Fal edit endpoint needs a source image,
so this calls the nano-banana-pro generate endpoint directly."""

import os
from films.woods_of_west import script


def _generate_still(prompt: str, out_path: str, aspect_ratio: str = "16:9",
                    resolution: str = "2K") -> str:
    """Text-to-image via Fal nano-banana-pro (Gemini 3 Pro Image). Endpoint is
    overridable via ILYRIUM_T2I_ENDPOINT; the result shape matches the studio's
    other fal calls (result["images"][i]["url"])."""
    if not os.getenv("FAL_KEY"):
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)
        except Exception:
            pass
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not set — cannot generate character sheets.")
    import fal_client
    import requests
    endpoint = os.getenv("ILYRIUM_T2I_ENDPOINT", "fal-ai/nano-banana-pro/text-to-image")
    result = fal_client.subscribe(
        endpoint,
        arguments={"prompt": prompt, "aspect_ratio": aspect_ratio,
                   "resolution": resolution, "num_images": 1},
        with_logs=True,
    )
    images = result.get("images") or []
    first = images[0] if images else None
    url = first.get("url") if isinstance(first, dict) else None
    if not url:
        raise RuntimeError(f"text-to-image returned no usable image url for {out_path}: {first!r}")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    d = requests.get(url, timeout=300)
    d.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(d.content)
    return out_path


def build_character_sheets(style: str, out_dir: str) -> dict:
    """Generate one reference sheet per character in `style`. Returns {char_id: png_path}."""
    os.makedirs(out_dir, exist_ok=True)
    refs = {}
    for cid, look in script.CHARACTERS.items():
        out_path = os.path.join(out_dir, f"{cid}_sheet.png")
        prompt = (f"{script.style_prefix(style)}, 16:9, full-body and face character "
                  f"reference sheet on a plain background: {look}")
        refs[cid] = _generate_still(prompt, out_path)
    return refs
