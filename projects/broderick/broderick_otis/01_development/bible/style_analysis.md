# Style Analysis — Otis the Hound Dog (SEED v0, 2026-06-11)

Panels examined: 01 (theme-song intro), 04 (the lunge), 05 (vet table END). 5 panels total in `panels/`.

## Medium determination

**Original hand-drawn digital cartoon (stylus), scratchy gag-cartoon pen style — same drawn family as Big Hair / Job Interview. NOT clip-art, NOT AI render.**

Evidence:
- Wobbly restated contours, quick grass scribbles, and hand-hatched sun rays; line confidence varies the way a fast stylus pass does.
- Otis is a consistent invented cartoon design recurring across panels with natural drift (patch shapes shift slightly) — drawn, not assembled.
- Two-tier rendering (dark foreground ink over faint pale background line) is a deliberate layered digital workflow.
- No watermarks, no stock art, no photographic texture, no model artifacts.

## Line / color / shading / lettering

- **Line:** scratchy thin pen for foreground figures; backgrounds drawn in the same hand but dropped to a pale ghost-gray opacity (house, fence, tree, sun, clinic fixtures). Grass rendered as quick tick clusters.
- **Color:** strict grayscale.
- **Shading:** flat light-gray washes — drop shadow under the trotting dog, tongue, collar; solid black graphic fills for ear/tail patches, nose, fang-mouth interior, music notes.
- **Lettering:** typeset bold italic all-caps comic font for the sung narration, prefixed with musical-note glyphs; no balloons (no spoken dialogue at all — the strip is a jingle). "END" in bold italic at lower right.

## Palette table

| Name | Hex (est.) | Where used |
|---|---|---|
| paper_white | #FFFFFF | sky, dog's body, exam table |
| sketch_ink | #2A2A2A | foreground linework, lettering |
| solid_black_patch | #111111 | ear/tail patches, nose, fanged maw, music notes |
| ghost_gray_bg | #C9C9C9 | background house/fence/tree/sun, clinic wall chart, window |
| wash_gray | #DEDEDE | drop shadows, tongue, collar, grass shading |

## Composition & framing habits

- Landscape panels (~4:3), borderless on white.
- Theme-song panels: wide shots, dog trotting laterally across frame at grass level, sun upper corner, notes floating, narration top-left — a repeating jingle-card template.
- The lunge panel breaks the template: tight medium shot, low angle, dog rearing huge with the boy pinned at frame left — while sun and music notes incongruously remain, which is the joke.
- Final panel goes clinical: flat eye-level medium-wide, vet and table centered, ghost-gray exam room, stillness after the bounce.

## Continuity risks

1. Otis's patch map (left ear black, tail tip black, white body) must stay fixed; generators will float the patches or add body spots.
2. The fanged lunge face is a different render mode for the same character — must be prompted as the same dog, not a new monster.
3. Ghost-gray background opacity is structural; if backgrounds come back at full ink the airy jingle look collapses.
4. Music notes must persist in EVERY yard panel, including the lunge — their incongruity carries the tone flip.
5. Billy's cap appears in some panels and not others in source; pick a canon (cap on) and hold it.

## Keep vs Fix for regeneration

**Keep:**
- Scratchy pen cartoon hound design with solid black patches and lolling tongue
- Two-tier ink: dark foreground over faint ghost-gray suburban background
- Jingle-card template (lateral trot, sun, floating notes, narration caps with note glyphs)
- The lunge panel's template break and the deadpan clinical END panel
- Grayscale-only treatment with flat washes

**Fix:**
- Lock Otis's patch placement across panels (drifts in source)
- Resolve Billy's cap on/off inconsistency
- Stabilize background ghost-gray value (varies between panels)
- Keep fang count/jaw shape repeatable for the lunge mode
