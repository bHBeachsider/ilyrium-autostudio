"""strip_compositor.py — assemble rendered panels + lettering into a finished comic strip.

Pure PIL (no GPU, no model). Takes a comic breakdown + one rendered image per panel and produces a
laid-out strip with a title card, gutters, caption boxes, and speech balloons placed in detected
white space (v1). Persona-agnostic; used by the creative loop after the Hand renders the panels.

Lettering source: each panel's `dialogue` may be labeled transcript text (CAPTION:/<SPEAKER>:/SIGN:);
parse_lettering() splits it into caption boxes (narration) and balloons (speech); SIGN/SFX are
in-art and skipped.
"""
import os
import re
import textwrap
from PIL import Image, ImageDraw, ImageFont

GUTTER = 28
PAD = 10
LAYOUTS = {1: (1, 1), 2: (1, 2), 3: (1, 3), 4: (2, 2), 5: (2, 3), 6: (2, 3),
           7: (3, 3), 8: (3, 3), 9: (3, 3)}
_FONTS = ["comicbd.ttf", "comic.ttf", "arialbd.ttf", "arial.ttf"]


def load_font(size: int):
    for name in _FONTS:
        p = os.path.join(r"C:\Windows\Fonts", name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def choose_layout(n: int):
    return LAYOUTS.get(n, ((n + 2) // 3, 3))


def parse_lettering(text: str) -> dict:
    """Split labeled transcript text into {'captions':[...], 'balloons':[(speaker,text),...]}."""
    captions, balloons = [], []
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if not ln or ln == "(no text)":
            continue
        m = re.match(r"(CAPTION|SIGN|SFX):\s*(.*)", ln, re.I)
        if m:
            if m.group(1).upper() == "CAPTION":
                captions.append(m.group(2).strip())
            continue  # SIGN / SFX are in-art
        m2 = re.match(r"<?([A-Za-z][A-Za-z0-9 _]{0,20})>?:\s*(.*)", ln)
        if m2 and m2.group(2):
            balloons.append((m2.group(1).strip(), m2.group(2).strip()))
        else:
            balloons.append((None, ln))
    return {"captions": captions, "balloons": balloons}


def _wrap(draw, text, font, max_w):
    """Wrap text to a pixel width; return list of lines."""
    cols = max(6, int(max_w / max(1, font.getbbox("M")[2])))
    lines = []
    for para in text.split("\n"):
        lines += textwrap.wrap(para, width=cols) or [""]
    # tighten: re-wrap by actual pixel width
    out = []
    for ln in lines:
        while draw.textlength(ln, font=font) > max_w and " " in ln:
            cut = ln.rsplit(" ", 1)[0]
            ln = cut
        out.append(ln)
    return out


def find_whitespace_slot(img: Image.Image, slot_w: int, slot_h: int):
    """v1 placement: return (x, y) of the whitest (emptiest) region that fits slot_w x slot_h."""
    small = img.convert("L").resize((64, 64))
    px = small.load()
    sw, sh = img.width / 64, img.height / 64
    win_w, win_h = max(1, int(slot_w / sw)), max(1, int(slot_h / sh))
    best, best_xy = -1.0, (img.width - slot_w - PAD, PAD)
    for gy in range(0, 64 - win_h, 3):
        for gx in range(0, 64 - win_w, 3):
            s = sum(px[gx + dx, gy + dy] for dy in range(0, win_h, 2) for dx in range(0, win_w, 2))
            if s > best:
                best, best_xy = s, (int(gx * sw), int(gy * sh))
    x = min(max(PAD, best_xy[0]), img.width - slot_w - PAD)
    y = min(max(PAD, best_xy[1]), img.height - slot_h - PAD)
    return x, y


def draw_caption_box(panel: Image.Image, lines, font, pos="top"):
    d = ImageDraw.Draw(panel)
    lh = font.getbbox("Mg")[3] + 4
    box_h = lh * len(lines) + PAD * 2
    y0 = PAD if pos == "top" else panel.height - box_h - PAD
    d.rectangle([PAD, y0, panel.width - PAD, y0 + box_h], fill="white", outline="black", width=2)
    y = y0 + PAD
    for ln in lines:
        d.text((PAD * 2, y), ln, fill="black", font=font)
        y += lh


def draw_balloon(panel: Image.Image, lines, font, slot):
    d = ImageDraw.Draw(panel)
    lh = font.getbbox("Mg")[3] + 4
    w = max((d.textlength(ln, font=font) for ln in lines), default=40) + PAD * 2
    h = lh * len(lines) + PAD * 2
    x, y = slot
    try:
        d.rounded_rectangle([x, y, x + w, y + h], radius=12, fill="white", outline="black", width=2)
    except AttributeError:  # very old Pillow
        d.rectangle([x, y, x + w, y + h], fill="white", outline="black", width=2)
    d.polygon([(x + w * 0.3, y + h), (x + w * 0.45, y + h), (x + w * 0.3, y + h + 14)],
              fill="white", outline="black")
    ty = y + PAD
    for ln in lines:
        d.text((x + PAD, ty), ln, fill="black", font=font)
        ty += lh


def letter_panel(panel: Image.Image, dialogue: str, font_size: int = 0):
    """Composite caption boxes + balloons onto one panel from its labeled text."""
    fs = font_size or max(14, panel.width // 28)
    font = load_font(fs)
    lett = parse_lettering(dialogue)
    d = ImageDraw.Draw(panel)
    if lett["captions"]:
        lines = _wrap(d, " ".join(lett["captions"]), font, panel.width - PAD * 4)
        draw_caption_box(panel, lines, font, "top")
    for speaker, text in lett["balloons"]:
        body = (f"{speaker}: {text}" if speaker and speaker not in ("SPEAKER", "NARRATOR") else text)
        lines = _wrap(d, body, font, panel.width * 0.55)
        bw = int(max((d.textlength(l, font=font) for l in lines), default=40) + PAD * 2)
        bh = int((font.getbbox("Mg")[3] + 4) * len(lines) + PAD * 2)
        draw_balloon(panel, lines, font, find_whitespace_slot(panel, bw, bh))
    return panel


def place_panel(canvas: Image.Image, img: Image.Image, box, border=0):
    bx0, by0, bx1, by1 = box
    cw, ch = bx1 - bx0, by1 - by0
    scaled = img.copy()
    scaled.thumbnail((cw, ch), Image.LANCZOS)
    ox = bx0 + (cw - scaled.width) // 2
    oy = by0 + (ch - scaled.height) // 2
    canvas.paste(scaled, (ox, oy))
    if border:
        ImageDraw.Draw(canvas).rectangle([bx0, by0, bx1, by1], outline="black", width=border)


def render_title_card(title: str, width: int, height: int = 90):
    card = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(card)
    d.rectangle([2, 2, width - 3, height - 3], outline="black", width=3)
    font = load_font(max(22, height // 3))
    tw = d.textlength(title, font=font)
    d.text(((width - tw) // 2, height // 2 - font.getbbox("Mg")[3] // 2), title, fill="black", font=font)
    return card


def compose_strip(comic: dict, panel_images: dict, *, cell=(512, 512), border=1) -> Image.Image:
    panels = sorted(comic.get("panels", []), key=lambda p: p.get("n", 0))
    n = len(panels)
    rows, cols = choose_layout(n)
    cw, ch = cell
    title = comic.get("title")
    title_h = 90 if title else 0
    W = cols * cw + (cols + 1) * GUTTER
    H = title_h + rows * ch + (rows + 1) * GUTTER
    canvas = Image.new("RGB", (W, H), "white")
    if title:
        canvas.paste(render_title_card(title, W - 2 * GUTTER, title_h), (GUTTER, GUTTER // 2))
    for i, p in enumerate(panels):
        r, c = divmod(i, cols)
        x0 = GUTTER + c * (cw + GUTTER)
        y0 = title_h + GUTTER + r * (ch + GUTTER)
        img = panel_images.get(p.get("n")) or placeholder_panel(p.get("content", ""), cell)
        img = letter_panel(img.convert("RGB").resize(cell), p.get("dialogue") or "")
        place_panel(canvas, img, (x0, y0, x0 + cw, y0 + ch), border)
    return canvas


def placeholder_panel(text: str, size=(512, 512)) -> Image.Image:
    """Stand-in art for dry-run validation (no GPU): the staging description on a gray card."""
    img = Image.new("RGB", size, (208, 208, 208))
    d = ImageDraw.Draw(img)
    font = load_font(max(12, size[0] // 36))
    lines = _wrap(d, "[art] " + (text or ""), font, size[0] - 40)[:10]
    y = size[1] // 2 - len(lines) * 10
    for ln in lines:
        d.text((20, y), ln, fill=(90, 90, 90), font=font)
        y += font.getbbox("Mg")[3] + 4
    return img


def save_strip(img: Image.Image, meta: dict, out_path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path)
    import json
    with open(out_path.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return out_path
