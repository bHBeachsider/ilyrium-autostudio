# Style Analysis — Memory Lane (Where Are They Now?) (SEED v0, 2026-06-11)

Panels sampled: all 3 (Gary classroom, Doreen hallway, Flapjacks portrait/END).

## Medium determination
**Hand-drawn digital caricature ink, black-and-white with flat gray washes.** Evidence:
scratchy freehand contours with visible stroke overdraw; deliberately ugly exaggerated
faces (acne pustules drawn one by one, individual buck teeth); background figures
knocked back to pale gray outline via layer opacity — a digital-workflow signature;
flat untextured gray fills on clothing. The script "Where Are They Now?" banner is a
typeset/calligraphic title element distinct from the drawn art. No photo texture, no
3D, no AI artifacts.

## Line / color / shading / lettering
- **Line:** rough scratchy pen, medium-heavy on subjects, with quick hatch strokes for
  hair, knuckles, fabric folds; backgrounds and witnesses in thin pale gray line.
- **Color:** none — strict grayscale.
- **Shading:** flat gray washes block in garments (skirt, sweater, football); a darker
  gray for hair masses; no gradients, no cast shadows; white page does the staging.
- **Lettering:** two systems — (1) elegant white script on a black banner for the
  series title (yearbook parody register), (2) hand-drawn all-caps caption bands for
  the deadpan biographies, top or side of panel. Vertical black END bar with stacked
  white letters on the final panel's right edge.

## Palette table
| Name | Hex est. | Where used |
|---|---|---|
| ink_black | #151515 | subject linework, title banner, END bar, sweater body |
| paper_white | #ffffff | page ground, caption fields, banner script |
| ghost_gray | #c0c0c0 | faded background witnesses |
| wash_gray | #9a9a9a | flat clothing fills, football |
| shadow_gray | #6e6e6e | hair masses, darker garment accents |

## Composition & framing habits
- One subject per panel, centered, at near-full weight; one or two witnesses faded to
  ghost gray as social context — a hierarchy-by-line-weight device.
- No environments: a desk, a prop, white space. The caption text owns 20-35% of each
  panel's real estate and is part of the composition.
- Panel 3 uses a slight low angle to inflate the jock's swagger; panel 2 is a flat
  full-shot fashion-plate pose. Static, portrait-first staging throughout.
- Anthology structure: no character recurs; black banner opens, vertical END bar closes.

## Continuity risks
1. Caricature ugliness is the style — engines will prettify Doreen and de-acne
   Flapjacks; the joke dies.
2. Ghost-gray witness fade must survive regeneration; full-weight backgrounds flatten
   the visual hierarchy.
3. Caption real estate must be reserved at layout time (top band, side column) before
   art generation, or the text pass will collide with figures.
4. Letterman "D", wristband, hoop earrings are per-character identity props — restate
   them every prompt.
5. Two lettering systems (script banner vs caps captions) must not blend.

## Keep vs fix (for regeneration)
**Keep:** subject-vs-witness line-weight hierarchy; white-page staging with no sets;
flat gray garment washes; gleefully ugly caricature; script-on-black series banner;
all-caps caption biographies; vertical END bar.
**Fix:** generate art textless with reserved caption zones, letter in post; treat the
script banner as a reusable design asset, not generated art; per-panel prompt must
explicitly demand exaggerated unflattering features; pin gray values (subject wash vs
witness fade) so tonal hierarchy is consistent across the three panels.
