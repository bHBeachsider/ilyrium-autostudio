# Strip Compositor — Spec

## Goal & position in the loop
Take the Brain's panel breakdown + the Hand-rendered panel images and assemble a **finished
multi-panel strip**: lay out the panels, add gutters/borders + a title card, and **composite the
lettering in post** (caption boxes + speech balloons) — because diffusion can't render legible text
reliably (same reason the Nast loop composites its caption banner). This is the final stage:

```
premise → Brain (breakdown) → Hand (style + character LoRAs render each panel) → STRIP COMPOSITOR → finished strip.png
```

**Persona-agnostic + pure PIL — no GPU, no model, no API.** It runs anywhere and is the single most
immediately buildable component. Implementation home: the shared creative loop
`apps/satirist/satirist/strip_compositor.py` (extends the existing `caption.py`), not the persona pack.

## Data contract
**In:**
- `comic` JSON (Brain output): `{format, comedic_thesis, title?, panels:[{n, beat, content, dialogue, characters_present?, balloon_hint?}]}`.
- `panels`: rendered PNG per panel, keyed by `n` (the Hand's output, style+character LoRAs already applied).

**Out:** one finished `strip.png` + a sidecar `strip.json` (the comic JSON + layout used + font/version).

## Layout engine
- **Tier layout** by panel count: 1→1×1, 2→1×2, 3→1×3, 4→2×2, 5–6→2×3, 7–9→3×3 (config-overridable;
  `multi_strip` stacks tiers). Aim for a readable aspect ratio.
- Uniform panel cell (scale/letterbox each render to the cell), **gutters** (~24–40px white),
  optional **panel borders** (Broderick reads as borderless/white-void — border width default 0–2px,
  configurable).
- **Title card** (panel 0, full-width banner): his signature memoir framing — e.g.
  `"Snapshots of Life — No. 707B"` from `comic.title`. Distinct typeface from the body lettering.
- Reading order is left-to-right, top-to-bottom by panel `n`.

## Lettering — caption boxes + balloons (the real work)
The Brain/transcripts already separate **CAPTION** (narration), **dialogue** (per speaker), and
**SIGN** (in-art — left to the render). The compositor places:
- **Caption boxes**: rectangular box, top (or bottom) of the panel, narration text, wrapped, a thin
  border — the Broderick caption-box look.
- **Speech balloons**: rounded rectangle (`ImageDraw.rounded_rectangle`) + a triangular **tail**,
  dialogue wrapped inside, auto-sized font to fit.
- **Font**: a hand-lettered comic font (bundle a license-clean one, e.g. an open comic face) to match
  his lettering; ALL-CAPS to match the corpus. Title card uses a heavier display face.

### The hard part — balloon placement (be honest)
Auto-placing balloons **without occluding faces/art** is the genuine difficulty. Tiers:
- **v1 (ship first):** structured zones — caption box pinned to the panel top; dialogue balloons in a
  **white-space slot** found by a cheap image scan (downscale → find the largest near-white region →
  place the balloon there). Broderick's heavy white-void staging *helps* — there's usually room.
- **v2:** rank multiple candidate slots by whiteness × distance-from-face (a light face-detector or
  saliency map avoids covering the caricature); pick best; auto-route the tail toward the speaker side.
- **v3:** the Brain emits a `balloon_hint` per line (e.g. `"top-left"`) or the renderer reserves a
  region; the compositor honors it.
Start at v1; it's robust given his style. Multi-balloon panels: stack vertically in reading order.

## Output & options
- `compose_strip(comic, panel_images, out_path, *, layout=None, border=0, font=...) -> str`
- Flags: `--no-lettering` (clean art only), `--layout 2x3`, `--caption-pos top|bottom`.

## Implementation sketch (`apps/satirist/satirist/strip_compositor.py`)
Pure functions (unit-testable on tiny in-memory images, no GPU):
- `choose_layout(n) -> (rows, cols)`
- `place_panel(canvas, img, cell)` — scale/letterbox into a cell
- `draw_caption_box(panel, text, pos)` / `draw_balloon(panel, text, slot, tail_to)`
- `find_whitespace_slot(panel_img) -> bbox` (v1 placement)
- `compose_strip(comic, panel_images, …) -> Image` (orchestrates) + `save_strip(img, meta, out)`
- `render_title_card(title) -> Image`

## Evaluation
- **Legibility**: all caption/dialogue readable at output resolution.
- **No occlusion**: balloons don't cover faces/key art (v2 metric; v1 spot-check).
- **Reading order**: panels + balloons read in the intended sequence.
- **Looks like a Broderick strip**: title card + caption-box density + white gutters; HITL eyeball.
- Unit tests: layout math, wrapping, whitespace-slot finder on synthetic panels.

## Honest limits
- v1 balloon placement is heuristic — dense or speaker-ambiguous panels need v2 or a `balloon_hint`.
- Tail-to-mouth precision needs speaker coordinates the render doesn't currently emit (v2/v3).
- Font choice strongly affects "is this Broderick" — worth a pass with him on the lettering face.

## Sequencing
1. **Now (no GPU):** build v1 — layout + caption boxes + white-space-slot balloons + title card; unit
   tests; dry-run on the existing transcripts (use the panel captions as stand-in art) to validate
   layout/lettering before any GPU render.
2. With the Hand online: composite real rendered panels end-to-end.
3. v2 placement (face-aware) once v1 strips look right.
