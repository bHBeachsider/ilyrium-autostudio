# Style Analysis — Poetry (ˈpoʊətri) (SEED v0, 2026-06-11)

Panels sampled: all 4 source images (each a 3-vignette row; 12 vignettes total covered).

## Medium determination
**Hand-drawn digital (iPad/Procreate-class), full saturated color.** Evidence: wobbly
freehand black contours of inconsistent weight; flat marker-style fills with visible
streaking inside shapes (cardigan, suit); deliberate grotesque caricature that no
photoreal pipeline produces; hand-drawn lettering with irregular letterforms; the
Mellow Yellow bokeh background is a simple digital soft-brush dab pattern, not
photographic bokeh. No 3D shading, no AI texture artifacts.

## Line / color / shading / lettering
- **Line:** confident but loose black ink, medium weight, wobble left in; contours
  occasionally gapped; interior detail (wrinkles, stubble, jowls) as quick scratchy
  strokes.
- **Color:** loud, saturated, flat. Each vignette sits on a single flat color field;
  garments in bold primaries/secondaries (green cardigan, red shirt, purple suit,
  navy sweater). Faces ruddy-flesh with pink-red blotching on noses and cheeks.
- **Shading:** essentially none — flat fills with at most a darker streak; sunset and
  bokeh backdrops are the only gradients (Hanky-Panky, Mellow Yellow).
- **Lettering:** chunky hand-drawn all-caps titles, one per vignette, color-matched or
  contrast-matched to the panel (orange, white-on-black, yellow/black, red, purple);
  arced ("FUDDY DUDDY"), stacked ("PENCIL CLUB"), or split across corners ("HERE &
  THERE"). One spoken line ("WOT DAT DAYAR") set in white caps on the silhouette.

## Palette table
| Name | Hex est. | Where used |
|---|---|---|
| mustard_field | #e9b62c | Nutty Putty bg, Six-Foot Sub banner, Wiggly Arm bg |
| flat_periwinkle | #6b86d6 | Fuddy Duddy and Cap'n Stanky backdrops |
| magenta_bokeh | #a83a9b | Mellow Yellow bokeh; Hanky-Panky sunset core |
| lavender_panel | #9e93c8 | Fix the Cello backdrop |
| showman_purple | #8e44ad | Here & There suit + lettering |
| ruddy_flesh | #e0a58e | caricature skin, blotched noses/cheeks/jowls |

## Composition & framing habits
- Strict three-vignette rows; each vignette a bust or full-figure portrait, straight-on,
  centered, museum-plaque presentation.
- Figure fills 60-80% of panel height; title lettering wedged into remaining negative
  space, never overlapping the face.
- Only two vignettes have any scene depth (classroom over-the-shoulder; dinner plate
  high-angle); everything else is flat color field + figure + title.
- No panel-to-panel continuity — it is an anthology; each figure appears exactly once.

## Continuity risks
1. Anthology format means per-panel character lock matters more than cross-panel lock:
   each vignette must nail its one description in one shot.
2. Caricature intensity drift — engines regress to pleasant faces; the grotesque
   (bulbous pocked nose, gold tooth, drooping jowls) is the style.
3. Background discipline — engines will invent rooms; all but two panels are flat
   color fields.
4. Per-panel title color/placement is part of the design; lettering pass must vary
   per vignette, not standardize.
5. Wiggly Arm's stripes must follow the arm's S-curves — easy failure point.

## Keep vs fix (for regeneration)
**Keep:** flat single-color panel grounds; grotesque caricature scale; loud flat
garment colors; hand-drawn per-panel title treatments; three-across row layout;
straight-on portrait framing.
**Fix:** generate textless and letter in post (titles are too design-specific for
in-model text); add explicit "flat color background, no environment" to every prompt;
boost caricature adjectives per character; render Hanky-Panky and Mellow Yellow with
their gradient/bokeh backdrops described explicitly as the only non-flat grounds.
