# Style Analysis — He Goes Like This (SEED v0, 2026-06-11)

Panels examined: 01 (first pose + title header), 03 (horizontal lean pose), 05 (red-tears END). 5 panels total in `panels/`.

## Medium determination

**Hand-drawn digital cartoon (stylus), thin-pen single-figure caricature. NOT clip-art, NOT AI render.**

Evidence:
- Thin scratchy contour with restated strokes (sleeve cuffs, trouser pleats); hands drawn as quick splayed-finger gestures with natural irregularity.
- The figure is a deliberate caricature construction — oversized realistic-ish face on a tiny wiry body — held consistent across panels with hand drift; AI renders don't keep this proportion gag stable, and there are no model artifacts.
- The floor is an unapologetic gray scribble, and the face shading is sparse hatching — fast stylus marks.
- Solid black turtleneck/hair fill dropped under the line is a layered digital workflow.

## Line / color / shading / lettering

- **Line:** thin, slightly nervous pen; more delicate than the other strips in the family. Facial features semi-realistic (modeled nose, brow shadow) against a deliberately crude body.
- **Color:** monochrome until the last panel, where bloodshot red eye rims and streaming red tears appear — the strip's only color, doing all the emotional work.
- **Shading:** solid black fill (turtleneck, hair), pale flat gray wash (trousers, shoes), gray scribble shadow underfoot. Light hatch on the face.
- **Lettering:** thin letterspaced caps in a casual handwriting-style font — NOT the bold italic comic font of sibling strips. Panel 1 carries a top-left title header ("HE GOES LIKE THIS"); narration floats beside the figure with trailing ellipses; a small solid black arrow points at the tears in the final panel; END in heavier casual caps bottom-right.

## Palette table

| Name | Hex (est.) | Where used |
|---|---|---|
| void_white | #FFFFFF | entire field, all panels |
| pen_ink | #1E1E1E | linework, lettering, callout arrow |
| turtleneck_black | #161616 | turtleneck and hair solid fills |
| trouser_gray | #CFCFCF | trousers, shoes, scribbled floor shadow |
| tear_red | #D62718 | final panel only — eye rims and tears |

## Composition & framing habits

- Square panels, borderless white void; one full-body figure per panel, roughly centered, occupying about a third of the frame height — enormous negative space.
- Pose-per-panel grammar: each panel is one frozen dance position; narration alternates "like this... / like that..." beside the head.
- No environment whatsoever except the scribble shadow; the eye has nowhere to go but the pose.
- Final panel keeps the identical grammar — same scale, same void — and changes only the eyes, plus a deadpan arrow making sure you notice. The restraint is the punchline.

## Continuity risks

1. The head-to-body ratio is the character; generators will normalize proportions. State "comically oversized head on small lean body" every prompt.
2. The face is semi-realistic — likeness drift toward a real person is possible; enforce the legal rule and regenerate on resemblance.
3. The red tears must be the ONLY color in the entire strip; color bleed into earlier panels destroys the ending.
4. Lettering font differs from sibling strips (thin handwriting caps, not bold comic italic) — don't let a shared lettering pass homogenize it.
5. Turtleneck must stay a flat solid black mass; rendered fabric folds break the graphic anchor.

## Keep vs Fix for regeneration

**Keep:**
- Oversized-head caricature on wiry body, solid black turtleneck + hair
- One-pose-per-panel grammar with centered figure and huge white void
- Gray scribble floor shadow as the only environment
- Thin letterspaced handwriting-caps narration with ellipses; black callout arrow
- Red tears as the strip's single color event in the final panel

**Fix:**
- Stabilize head size and facial structure between panels (drifts in source)
- Standardize trouser wash value (varies panel to panel)
- Keep hand/finger count clean in splayed gesture poses (source hands get loose)
- Decide a fixed scale/baseline so poses sit at a consistent height across panels
