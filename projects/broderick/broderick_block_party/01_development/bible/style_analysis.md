# Style Analysis — Neighborhood Block Party (SEED v0, 2026-06-11)

Panels examined: 01 (title card), 03 (grill confrontation), 05 (sports bros), 09 (end card). 4 of 9 panels.

## Medium Determination
**Hand-drawn digital illustration, grayscale only.** Evidence:
- Line weight varies organically within a single stroke (Dennis's shirt collar, Dan's slacks) — characteristic of pressure-sensitive stylus work, not vector or AI render.
- Scribbled, non-systematic crosshatching on faces, knees, and hair — an AI render would produce more uniform texture; a vector tool would produce cleaner hatching.
- Anatomy is deliberately caricatured and "wrong" in consistent ways (Dennis's tiny hunched frame, enormous head, panel 09's noodle arms) — stylistic intent, not generation artifact.
- Zero color in any panel. This contradicts the prior kernel's "flat color fills" claim — **the strip is monochrome**.

## Line / Color / Shading / Lettering
- **Line:** Confident scratchy ink, medium-to-heavy weight on figures, very light loose sketch on backgrounds. Strokes overshoot and double back (sketch energy left in).
- **Color:** None. Tonal grayscale: white paper, ~3 gray values, near-black ink.
- **Shading:** Flat mid-gray fills on dark garments; soft light-gray wash modeling on skin and metal (grill); scribble-hatch for texture and rage lines. No gradients to black, no cast shadows on ground (except the splat burst in 09).
- **Lettering:** All-caps hand lettering, slightly irregular baseline, floating free in white space — **no balloon outlines**; attribution by proximity and occasional thin pointer line (panel 05). Titles/end cards in giant bold brush-marker caps occupying ~40-50% of frame. Title card includes a dense mock-legalese fine-print block as a gag element.

## Palette Table
| Name | Hex est. | Where used |
|---|---|---|
| ink_black | #1A1A1A | linework, glasses, hair, display lettering |
| shirt_gray | #8C8C8C | Dennis's camp shirt, dark polos — darkest mass |
| wash_gray | #C4C4C4 | skin shading, slacks, grill body, shorts |
| sketch_gray | #DBDBDB | background houses, trees, shrubs |
| paper_white | #FFFFFF | negative space, lettering field, light polos |

## Composition & Framing
- Single panels, no border box; art bleeds into white page.
- Strong foreground figure (often Dennis in close-up, left or right third) with reactors in mid-ground; backgrounds dissolve to faint sketch within one depth plane.
- Eye-level medium shots dominate; title/end cards split frame between figure and display type.
- Generous white space is structural — lettering lives in it.

## Continuity Risks
1. Dennis's glasses (thick black rectangles) and spiky hair are the identity anchors — drift here breaks recognition instantly.
2. Polo-shirt neighbors are differentiated almost solely by shirt value (light vs dark vs white) and build; gray values must stay consistent per character.
3. Background fade level: if backgrounds render at figure-level line weight, the depth system collapses.
4. Any color introduction is a hard style break.
5. Lettering: generated text will garble — always letter in post.

## Keep vs Fix (for regeneration)
**Keep:** grayscale tonal system; scratchy variable line; caricature proportions; borderless panels; floating all-caps lettering; faded sketch suburbs; deadpan staging (flat eye-level, reactors frozen).
**Fix:** prior kernel's "flat color fills" descriptor (wrong — monochrome); ensure consistent gray value per garment across panels (source drifts slightly); stabilize Dennis's head/body ratio between close-ups and full-body shots (panel 09 is more extreme than panel 01); keep fine-print gag as post-typography, never generated.
