# Style Analysis — Le Monde Extérieur (SEED v0, 2026-06-11)

Panels sampled: 01 (img_1519), 09 (img_1528), 11 (img_1530), 17 (img_1555) of 17.

## Medium determination
**Hand-drawn digital (iPad/Procreate-class), grayscale.** Evidence: visible freehand
contour wobble on the railing bars and tree branches; looping scribble texture on the
shrubs that no AI render produces consistently; flat untextured gray fills with hard
edges; identical background plate redrawn (not cloned — small line variances) across
panels; hand-lettered all-caps balloons with irregular letter widths. No photographic
texture, no gradient lighting, no AI artifacting.

## Line / color / shading / lettering
- **Line:** bold, confident, variable-width black ink; thicker on foreground (railing,
  smoker's silhouette), thinner on background houses. Loose scribble-hatch for shrubs
  and the smoker's chair back.
- **Color:** none — strict grayscale. Tonal bands carry depth: white sky → pale street
  → mid-gray houses → near-black foreground.
- **Shading:** flat fills only; no gradients, no cast shadows except light scuff/motion
  marks. Smoke rendered as a single thin wavering line.
- **Lettering:** hand-drawn all-caps, white rounded-rectangle balloons with thick black
  borders and short pointed tails. SFX ("HONNNKKK", "HONK HONK HONK") as enormous
  freehand outline letters arcing across the sky. Black "END" card, white knockout type,
  bottom-right of final panel.

## Palette table
| Name | Hex est. | Where used |
|---|---|---|
| ink_black | #1a1a1a | contours, railing, suit, lettering, END card |
| house_gray | #7d7d7d | ranch houses, parked cars, distant trees |
| street_pale | #d8d8d8 | road surface, sidewalk |
| paper_white | #ffffff | sky, balloon interiors, highlights |
| scribble_shrub | #9e9e9e | foreground shrub scribble texture |
| smoke_curl | #b5b5b5 | cigarette smoke line |

## Composition & framing habits
- One locked camera: over-the-shoulder from the porch, eye level, the bald smoker's
  back anchoring bottom-center, iron railing + shrubs as a foreground proscenium.
- The street is a horizontal stage band across the middle third; action enters and
  exits left/right like theater wings.
- Vehicle panels break the calm with diagonal mass (sedan/truck filling the right
  third) while the porch foreground stays identical — the contrast IS the gag.
- Repetition with micro-variation; the smoker almost never moves.

## Continuity risks
1. Background plate drift (house/tree placement) between generated panels — the gag
   depends on a near-identical set; consider a locked background plate composited
   under per-panel figures.
2. Street man's two poses (lunge vs hip-wiggle stroll) must stay exactly two poses;
   pose invention dilutes the ritual.
3. Smoker's sparse hair strands (3-5 wiry lines) and cigarette-in-right-hand are
   identity anchors; easily lost.
4. Grayscale discipline — engines love to sneak in color or gradient light.
5. Tire marks introduced in scene 12 must persist through scenes 13-17.

## Keep vs fix (for regeneration)
**Keep:** locked porch POV; strict grayscale flats; scribble shrubs; thin smoke line;
hand-lettered balloons + giant SFX; two-pose street-man vocabulary; END card.
**Fix:** lock a reusable background plate; generate art textless and letter in post;
enforce monochrome via negatives; pin tire-mark continuity after scene 12; model-sheet
the smoker's back-of-head before batch render.
