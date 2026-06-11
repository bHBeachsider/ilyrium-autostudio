# Style Analysis — Slow on the Uptake (SEED v0, 2026-06-11)

Panels examined: 01 (boss tirade), 04 (courthouse, "ARE YOU DAVID?"), 08 (firing tirade — dialogue-heavy), 09 (unemployment end card). 4 of 9 panels.

## Medium Determination
**Hand-drawn digital sketch, grayscale.** The UUID-1024x1024 filenames suggested AI generation, but the art itself is clearly hand-drawn: line wobble and hesitation are continuous and human (clerk's egg head outline, panel 04); anatomy errors are consistent per character across panels (the boss's wedge nose, the clerk's tuft) rather than random per-image; lettering is the same hand throughout; shading is loose directional marker swipes, not diffusion texture. Filenames are most plausibly CMS/upload artifacts from whyarewealive.com.

## Line / Color / Shading / Lettering
- **Line:** Thin-to-medium wobbly digital ink, naive and quick; limbs are noodles, hands are mitten-simple. Less controlled and less textured than the Block Party strip — this is the looser end of the Broderick house style.
- **Color:** None. Pure grayscale.
- **Shading:** Sparse. Quick gray marker swipes under chins, on shirt folds, sweat shadows, and desk surfaces (diagonal hatch strokes in panel 08). Most surfaces left paper-white.
- **Solid blacks:** Trousers, ties, hair masses, and display lettering are flat filled black — they anchor compositions against all the white.
- **Lettering:** Bold all-caps hand lettering; long speeches sit as a caption block across the top (panels 01, 08) with underlined emphasis words ("AFFIDAVIT", "IN MY HAND"); short exchanges float beside heads with no balloons. "END" in chunky brush caps.

## Palette Table
| Name | Hex est. | Where used |
|---|---|---|
| ink_black | #1F1F1F | contours, features, lettering |
| fill_black | #111111 | trousers, ties, hair, END type |
| swipe_gray | #BFBFBF | shading swipes, sweat shadows, desk hatch |
| sketch_gray | #D8D8D8 | ghosted courthouse facade, background figures |
| paper_white | #FFFFFF | dominant field; shirts/skin unfilled |

## Composition & Framing
- Borderless single panels drowning in white space; figures occupy lower two-thirds.
- Two-shots at eye level with generous gap between speakers; the gap is the deadpan beat.
- Backgrounds appear only when load-bearing (courthouse pediment, office desk) and are ghosted to near-invisibility.
- Caption-block-on-top layout whenever a speech is long; art shrinks to make room.

## Continuity Risks
1. Clerk's silhouette (egg head + tuft + black tie + black slacks) is the franchise anchor; the tuft disappears easily at small scale.
2. Boss vs clerk differentiation relies on nose shape and hair scribble — both balding men in shirt and tie.
3. Afro David's afro must stay an enormous clean round mass, not textured curls.
4. Generation tools will want to "finish" this style — add rendering, fix anatomy, tighten line. All of that breaks it.
5. Image sizes vary across source panels (256px thumbs vs 1024px) — train/reference from the 1024 set only.

## Keep vs Fix (for regeneration)
**Keep:** wobbly naive line; egg-head proportions; flat black garment fills; ghosted gray backgrounds; top caption-block lettering with underlines; white-dominated borderless frames.
**Fix:** source panel resolution inconsistency (use 1024px refs); slight character drift in the clerk's head shape between panels; do not let regeneration add crosshatch density or color; keep sweat beads as discrete flying drops, not gloss highlights.
