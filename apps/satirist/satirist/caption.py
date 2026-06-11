"""Caption banner composite (PIL) + artifact save. v1 does NOT overlay in-image labels
(SDXL can't render legible text); it adds a legible caption strip below the render."""
import json
import os
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont

_SENT = re.compile(r"(?<=[.!?])\s+")
_MAX = 160
_BANNER_PAD = 12
_LINE_H = 16


def derive_caption(text: str) -> str:
    """First sentence of the allegory rationale, truncated to <=160 chars."""
    text = (text or "").strip()
    first = _SENT.split(text)[0] if text else ""
    return first if len(first) <= _MAX else first[:_MAX - 1].rstrip() + "…"


def compose_caption_banner(image: Image.Image, caption: str) -> Image.Image:
    """Return a new RGB image = the render with a white caption strip appended below."""
    img = image.convert("RGB")
    try:
        font = ImageFont.load_default()
    except Exception:                                   # pragma: no cover - font always present
        font = None
    wrap_cols = max(10, img.width // 7)
    lines = textwrap.wrap(caption, width=wrap_cols) or [""]
    banner_h = _BANNER_PAD * 2 + _LINE_H * len(lines)
    out = Image.new("RGB", (img.width, img.height + banner_h), "white")
    out.paste(img, (0, 0))
    draw = ImageDraw.Draw(out)
    y = img.height + _BANNER_PAD
    for line in lines:
        draw.text((_BANNER_PAD, y), line, fill="black", font=font)
        y += _LINE_H
    return out


def save_artifact(image: Image.Image, meta: dict, out_dir: str, slug: str) -> str:
    """Write <slug>.png and <slug>.json into out_dir; return the PNG path."""
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, f"{slug}.png")
    image.save(png)
    with open(png[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return png
