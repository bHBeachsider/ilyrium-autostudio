# Style Analysis — Results (SEED v0, 2026-06-11)

Panels sampled: both source images (dieting_man diptych, facelift_woman diptych).

## Medium determination
**Hand-drawn digital ink cartoon, black-and-white, white void staging.** Evidence:
single-pass freehand contour with characteristic wobble and overdraw at joints; body
hair and strain lines as individual quick scratch strokes; pale gray accents are loose
digital soft-brush dabs that ignore the contour (a tablet-workflow tell); polka dots
hand-blobbed, irregular; both BEFORE/AFTER halves visibly redrawn rather than cloned
(line variance between halves). No photo texture, no gradients, no AI artifacts.

## Line / color / shading / lettering
- **Line:** confident single-weight ink, slightly heavier on silhouette; scratchy
  detail strokes for chest hair, knuckles, neck strain lines; thick ruler-straight
  vertical divider bar between halves.
- **Color:** none — black ink on white, one mid-gray garment fill.
- **Shading:** no true shading; loose pale-gray dabs float inside forms (belly, back,
  boxers, face) to suggest volume; no cast shadows, no floor line.
- **Lettering:** hand-drawn bold all-caps "BEFORE"/"AFTER" inside white outlined boxes
  (pedestal plaque for the man, chest label card for the woman); squiggle smoke marks
  over the cigarette.

## Palette table
| Name | Hex est. | Where used |
|---|---|---|
| ink_black | #0f0f0f | contours, polka dots, lips, label lettering |
| void_white | #ffffff | entire background, label fields |
| soft_gray_dab | #d4d4d4 | loose volume accents inside bodies/garments |
| garment_gray | #a9a9a9 | woman's high-collar top fill |
| divider_bar | #000000 | thick vertical BEFORE/AFTER rule |

## Composition & framing habits
- Strict diptych: two near-identical panels separated by a heavy vertical bar; the
  comedy is in the delta (or absence of one) between halves.
- Man: full-figure exact side profile on a labeled pedestal, eye level. Woman: bust
  portrait, straight-on, label card on chest, cigarette hand raised at frame edge.
- Total white void — no horizon, no shadow; the label object is the only set dressing.
- Affect is held deadpan in all four images; the AFTER face/body carries the entire
  gag.

## Continuity risks
1. THE risk: BEFORE/AFTER identity lock. Each subject must read as exactly the same
   person — glasses, mustache, tuft, boxers pattern; earrings/cigarette/nails. Use the
   BEFORE image as reference/init for the AFTER.
2. Pose and framing drift between halves kills the joke (the man's gag is that only
   the belly's height changes).
3. Engines will add floors, shadows, or studio backdrops — the void must stay empty.
4. The woman's AFTER is grotesque by design (skin topknot, strain lines); prettifying
   regression destroys the punchline.
5. Cigarette must persist unchanged in both of her panels — it is the stated
   continuity anchor.

## Keep vs fix (for regeneration)
**Keep:** white void staging; heavy vertical divider; single-weight ink + gray dabs;
deadpan held expressions; pedestal plaque / chest label devices; exact-profile and
straight-on framings.
**Fix:** generate each AFTER from its BEFORE as an image-to-image pass with the gag
delta described, never from scratch; generate textless and letter labels in post; add
explicit "blank white background, no floor, no shadow" to every prompt; model-sheet
both subjects (profile for the man, frontal for the woman) before batch work.
