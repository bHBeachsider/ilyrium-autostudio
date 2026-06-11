# Style Analysis — Big Hair (SEED v0, 2026-06-11)

Panels examined: 01 (interview rejection, dialogue-heavy), 02 (bar mockery, two-speaker), 05 (mug smash), 06 (aftermath END). 6 panels total in `panels/`.

## Medium determination

**Original hand-drawn digital cartoon (stylus/Procreate-class), scratchy gag-cartoon pen style. NOT clip-art collage, NOT AI render.**

Evidence:
- Linework is loose, multi-stroke, and inconsistently weighted — visible restated contours (chair, desk edges), open shapes, hatch scribbles. Characteristic of fast stylus drawing.
- Character designs are consistent caricatures recurring across panels (same droopy nose, same hair tangle) with natural drift — drawn, not assembled or sampled.
- Gray washes are flat digital fills dropped under the line layer (skyline, t-shirt, counter), a standard digital-cartoon workflow.
- No watermarks, no stock poses, no photographic texture anywhere.

## Line / color / shading / lettering

- **Line:** scratchy, nervous, energetic; thin pen weight with frequent double-strokes and sketch hatching (suit folds, hair ropes). The big hair is drawn as overlapping thick noodle strands.
- **Color:** strict grayscale. White ground, near-black ink, two flat gray values.
- **Shading:** flat light-gray fills only — no gradients, no rendering. Shadow is graphic (a gray block), not lit.
- **Lettering:** digital typeset bold italic all-caps comic font. Mostly free-floating without balloons; the voiceover caption ("UNWINDING AFTER A DAY OF REJECTION...") sits in a bordered box; emphasized words ("BIG HAIR") jump to a larger point size; END appears in a plain bordered white box. Speaker attribution by placement.

## Palette table

| Name | Hex (est.) | Where used |
|---|---|---|
| paper_white | #FFFFFF | background, every panel |
| sketch_ink | #2A2A2A | linework, lettering |
| wash_gray_light | #D9D9D9 | skyline silhouette, t-shirt, mirrored BAR sign, counter |
| wash_gray_mid | #BDBDBD | skin shading, mug glass, debris shadows |
| impact_burst | #1F1F1F | starburst, speed lines, flying teeth/glass (panel 5) |

## Composition & framing habits

- Square ~1:1 panels, borderless on white; environments are minimal — a window rectangle, a counter line, a mirrored "BAR" window sign that recurs as the location anchor.
- Dialogue panels: medium two-shots at eye level, speakers facing each other, text stacked in the upper third.
- The mug-smash panel breaks the grammar: tight close-up, low angle, frame packed edge-to-edge with debris — the only dense panel in the strip, which is what sells it.
- Final panel returns to wide stillness with heavy right-side emptiness where the loudmouth used to be — negative space as punchline.

## Continuity risks

1. The hair tangle is the franchise asset: strand thickness and silhouette must stay constant; generators will simplify it to generic curly hair.
2. Mirrored "BAR" window sign must read backwards consistently — easy for models to flip or garble.
3. The scratchy line will "clean up" under most generators; over-smooth output kills the style.
4. Gray-wash placement is semantic (t-shirt always gray, suit always white) — random wash assignment breaks character reads.
5. Lettering size-jump emphasis (BIG HAIR) is part of the voice; uniform type flattens the joke.

## Keep vs Fix for regeneration

**Keep:**
- Scratchy multi-stroke pen line and caricature proportions
- Grayscale-with-flat-gray-wash treatment, white void backgrounds
- Minimal scene anchors (window, counter, reversed BAR sign)
- Free-floating typeset caps with size-jump emphasis; bordered caption/END boxes
- Panel-5 grammar break: dense, debris-filled impact close-up

**Fix:**
- Stabilize big_hair_man's hair silhouette between panels (varies noticeably in source)
- Settle interviewer's desk/window geometry (perspective drifts)
- Normalize gray values (washes vary in lightness between source panels)
- Keep teeth/eye caricature consistent on bar_loudmouth (gap teeth count drifts)
