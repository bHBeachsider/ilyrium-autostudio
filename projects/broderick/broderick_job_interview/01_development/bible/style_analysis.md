# Style Analysis — Job Interview (SEED v0, 2026-06-11)

Panels examined: 01 (name question), 04 (rage explosion, dialogue-heavy), 05 (infomercial epilogue, last). 5 panels total in `panels/`.

## Medium determination

**Original hand-drawn digital cartoon (stylus), scratchy gag-cartoon pen style — same family as the Big Hair strip. NOT clip-art, NOT AI render.**

Evidence:
- Loose, restated pen contours with visible sketch energy (chair legs, desk edges drawn with quick straight-ish strokes, hatching on the desk side).
- Consistent recurring caricatures across panels with natural hand drift (interviewer's beard mass, Jason's glasses-and-combed-hair silhouette).
- Flat digital gray washes and solid black fills under the line layer — standard Procreate-class workflow; no watermarks, no stock poses, no model artifacts.
- Expressive cartooning grammar (blown-back hair, spittle lines, lunging diagonal) that AI renders don't compose this deliberately.

## Line / color / shading / lettering

- **Line:** thin scratchy pen, variable weight, fast and confident; furniture nearly ruled, figures wobblier. Hatch ticks for glass/desk shine.
- **Color:** strict grayscale.
- **Shading:** two-level — flat light-gray wash (suits, skin shadow, desk side) plus solid black graphic fills (beard, hair, chair back).
- **Lettering:** typeset bold italic all-caps comic font at panel top, no balloons; the screamed line opens with an oversized serif drop-cap "I" for volume. Epilogue panel mixes registers deliberately: hand-drawn rounded-rectangle UI button with plain text ("Click here for permanent subscription!*") and a strip of dense tiny legal fine print across the bottom — the typography itself is the joke.

## Palette table

| Name | Hex (est.) | Where used |
|---|---|---|
| paper_white | #FFFFFF | background, desk top, every panel |
| sketch_ink | #2A2A2A | linework, headline lettering |
| solid_black_fill | #111111 | beard, hosts' hair, swivel-chair back, drop-cap |
| wash_gray | #DCDCDC | desk side, suit/skin shading, t-shirt folds |
| fine_print_gray | #333333 | legal disclaimer line, UI button text |

## Composition & framing habits

- Square ~1:1 panels, borderless on white.
- The office is a locked two-shot: desk left, Jason on swivel chair right, eye level — held static for three panels so the rage lunge in panel 4 (diagonal across frame, slight low angle) lands as a violation.
- Tiny absurd prop detail (paper tent card under the desk in panel 4) rewards close reading.
- Epilogue jumps to infomercial grammar: direct-to-camera medium close two-shot, floating UI button left, fine print bottom — a format parody inside the strip.

## Continuity risks

1. Jason's rectangular glasses + combed hair and the interviewer's beard/bow-tie are the only identity anchors; generators will mutate them between panels.
2. The locked static staging of panels 1–3 is structural; re-framing each panel destroys the deadpan rhythm.
3. Drop-cap and fine-print typography are easy to garble — letter in post.
4. Solid-black vs gray-wash assignment is semantic (beard/hair/chair always solid black); inconsistent fills break reads.
5. The epilogue duo must stay clearly cartoon-grotesque (wink, fixed grin) without drifting toward real-person likeness.

## Keep vs Fix for regeneration

**Keep:**
- Scratchy hand-drawn pen caricature, grayscale, white void office
- Locked two-shot staging with panel-4 grammar break (lunge diagonal, spittle lines, blown-back hair)
- Solid-black graphic fills against light-gray washes
- Typeset caps + drop-cap emphasis; hand-drawn UI button + fine-print strip in the epilogue
- The tent-card sight gag and other tiny absurd props

**Fix:**
- Stabilize Jason's head proportions (varies between panels in source)
- Keep desk geometry/perspective consistent across the locked shots
- Clean up fine-print legibility at output resolution (currently near-illegible)
- Normalize wash value across panels
