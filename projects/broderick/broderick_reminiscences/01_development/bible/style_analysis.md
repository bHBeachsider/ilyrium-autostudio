# Style Analysis — Reminiscences (SEED v0, 2026-06-11)

Panels examined: all 3 in `panels/` (the complete strip), square 2048x2048 sources.

## Medium determination
**Hand-drawn digital pen sketch, single reused plate.** Evidence: the portrait is pixel-identical across all three panels — same stray scribble above the head, same hatch strokes on the collar, same chest squiggles — proving a copy-pasted base drawing with swapped text layers. The line is loose, searching, and overdrawn (double-traced shirt placket, scribbled hair wisps), unmistakably freehand. No fills, no gradients, no AI rendering artifacts. Lettering is a uniform typeset all-caps comic font; masthead is a clean typeset sans-serif — both digital text layers over the drawing.

## Line / color / shading / lettering
- **Line:** scribbly, energetic, single weight; contours overshoot and double back. Hair as wiry flick strokes; stubble as dot-dash texture.
- **Color:** none whatsoever. Black ink on white paper, full stop.
- **Shading:** sketch crosshatch only — massed on the forehead creases, eye pouches, jowl shadow, and shirt folds. Optical gray comes from stroke density, never from a fill or wash.
- **Lettering:** all-caps comic font, center-justified ragged column filling the right half of each panel; no balloons, no tails. The closing caption "(TO BE CONTINUED. OR NOT.)" sits bottom-right in the same font. Masthead: bold black sans-serif "Reminiscences" top-left over a thin full-width rule — a fake newspaper-column header.

## Palette table
| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | entire background, no exceptions |
| ink_black | #1A1A1A | linework, lettering, masthead |
| hatch_tone | #BFBFBF (optical) | brow, jowls, neck shadow, shirt folds — stroke density only |

## Composition and framing habits
- Square panel; masthead band across the top.
- Head-and-shoulders portrait anchored left at three-quarter angle, eyes nearly shut, mouth mid-word; cropped at the chest by the panel edge.
- Text column owns the right half, vertically centered against the face.
- Absolute stasis is the format: zero camera moves, zero pose changes, zero environment. The strip is a newspaper op-ed column that talks.

## Continuity risks
1. Any per-panel re-render of the head breaks the deadpan static-plate gag — the sameness IS the joke.
2. Drooping nearly-shut eyes tend to "open" under regeneration; lock them.
3. Color or gray-wash creep would destroy the newsprint look.
4. Masthead font/weight must not drift; it sells the fake-column conceit.
5. Text column length varies a lot (scene 2 is densest); font size must shrink to fit rather than the portrait moving.

## Keep vs fix for regeneration
**Keep:** single locked portrait plate; scribbly pen line and crosshatch; pure black-and-white; masthead + rule; balloon-less centered text column; three-quarter angle with near-shut eyes; "(TO BE CONTINUED. OR NOT.)" sign-off.
**Fix:** stray scribble mark floating above the head (plate artifact — keep or clean deliberately, but decide once); text column occasionally crowds the panel edge at maximum length; chest-area squiggle strokes read as noise at small sizes.
