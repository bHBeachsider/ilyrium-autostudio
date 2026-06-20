"""fal.ai text-driven image editor — the studio's maskless edit path.

Wraps the reusable repo-root helper (tools/fal/nano_banana_edit) so studio code
and MCP tools can do instruction edits ("add a horseshoe fringe", "swap the
background to a newsroom", "put a gold bracelet on the left wrist") on a still,
through nano-banana-pro/edit (Gemini 3 Pro Image). No GPU box, no masks.

Mirrors media.fal_renderer's contract: returns the saved image path, raises on
failure so the orchestrator can record the reason.
"""

import os
import sys

# tools/fal lives at the repo root: media -> auto-studio -> apps -> ilyrium-autostudio
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_FALDIR = os.path.join(_ROOT, "tools", "fal")
if _FALDIR not in sys.path:
    sys.path.insert(0, _FALDIR)


def edit_image_fal(prompt: str, images, output_path: str, *, resolution: str = "2K",
                   aspect_ratio: str = "auto", seed: int | None = None,
                   num_images: int = 1) -> list[str]:
    """Edit still image(s) by text instruction and save to `output_path`.

    images: a path/URL or list thereof (multi-reference edits supported).
    Returns the list of saved local paths. Raises RuntimeError if FAL_KEY is
    unset (studio_mcp loads it from .env) or fal returns nothing usable.
    """
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not set — cannot call fal.ai image edit.")
    import nano_banana_edit  # lazy: only when actually editing
    return nano_banana_edit.edit_image(
        prompt, images, out=output_path, resolution=resolution,
        aspect_ratio=aspect_ratio, seed=seed, num_images=num_images,
    )
