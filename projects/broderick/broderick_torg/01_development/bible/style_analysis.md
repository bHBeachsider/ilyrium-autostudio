# Style Analysis — Torg the Defrosted Neanderthal (SEED v0, 2026-06-11)

Panels sampled: 01 (intro caption + likes lesson, dialogue-heavy), 02 (second lesson beat), 04 (gibberish punchline + END). 3 of 4 total panels (panel 03 is a held silent repeat of the same composition).

## Medium Determination
**Hand-drawn digital, sketchy pen style, strict grayscale.** Evidence:
- Linework is loose and scratchy with visible scribbled hatching building Torg's musculature, matted hair, and beard — individual overlapping strokes are clearly hand-laid, not vector-smooth or AI-render.
- Construction roughness survives in the final art (fingers, hair tangles, spear lashing) — sketch energy is the style, not a defect.
- Flat light-gray washes are dropped in sparsely and digitally (uniform value, hard edges) under the pen work.
- Lettering is a typeset all-caps comic font (consistent letterforms across panels) — digital lettering pass over hand art.
- No color anywhere; the strip is ink-on-white with two gray values.

## Line / Color / Shading / Lettering
- **Line:** Scratchy, energetic, variable; heavier contour on figure silhouettes, dense scribble-hatching for hair/beard/muscle shadow, fine nervous lines for the social-feed mock-up on the monitor.
- **Color:** None. White paper, near-black ink, one flat light gray wash, plus the optical mid-gray of hatching density.
- **Shading:** Hatch-based modeling on Torg (the visual heavyweight); the instructor is rendered much lighter, almost pure contour — deliberate textural contrast between the two characters.
- **Lettering:** Clean typeset all-caps comic font; underline emphasis (LIKES); rounded-corner bordered narration box (panel 01 top); long borderless mock-documentary caption block (panel 04); bordered rectangular END plate.

## Palette Table
| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | Entire background void; instructor's top |
| ink_black | #1A1A1A | All line, hatching, monitor frame, lettering, END border |
| wash_gray | #D6D6D6 | Torg's flank shadow, hair mass, sleeve, screen tint |
| hatch_gray | #8F8F8F | Optical tone from scribbled hatching (muscle, beard, spear) |
| screen_thumbnails | #EFEFEF | Social-feed mock post cards on the monitor (recurring prop) |

## Composition & Framing Habits
- ONE composition for the whole strip: eye-level medium two-shot — monitor at frame left, instructor pointing at center, Torg looming at right. Held static across all four beats; this repetition IS the joke engine.
- No room, no floor, no furniture: white void plus the monitor on its stand.
- Strong size contrast: Torg fills the right third floor-to-ceiling; the instructor tucks under his spear arm.
- The spear bisects the frame vertically between the two characters in every panel.
- Text occupies the upper white space; art holds the lower two-thirds.
- Panel 04 zooms slightly wider/higher-res with a circular "tap" callout on the screen — the only framing variance.

## Continuity Risks
1. The static two-shot must NOT vary between beats — generators will "improve" the staging; identical composition is load-bearing for the deadpan timing.
2. Torg's hatching density and anatomy (brow, jaw, crooked lower teeth) must stay consistent; models drift cavemen toward cute or gorilla-like.
3. The spear: tall wooden shaft, leaf-shaped knapped stone point, lashed binding — never a club, never absent.
4. The instructor stays near-contour-only (minimal shading); equalizing render weight between characters flattens the visual joke.
5. The monitor feed is a loose line-sketch mock-up with stick-figure thumbnails — must not become a realistic UI screenshot.
6. Grayscale discipline: no color drift.

## Keep vs Fix (for regeneration)
**Keep:**
- Scratchy hatched pen style; sketch energy; ink-on-white with sparse flat gray wash.
- Held static two-shot repetition for timing.
- Torg heavy/textured vs instructor light/clean rendering contrast.
- Typeset all-caps comic-font captions, rounded narration box, bordered END plate.
- White-void staging with single monitor prop.

**Fix:**
- Panel 04 is higher resolution and slightly tighter line discipline than 01/02 — normalize stroke weight across beats.
- Wash placement is inconsistent (Torg's gray patches migrate between panels) — lock a wash map per character.
- Monitor screen contents shift slightly panel to panel — freeze one feed mock-up asset.
- Long caption blocks should be lettered in post; too much text for in-render fidelity.
