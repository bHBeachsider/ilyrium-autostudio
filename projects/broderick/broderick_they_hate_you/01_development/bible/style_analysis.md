# Style Analysis — They Hate You If You're Clever (SEED v0, 2026-06-11)

Panels sampled: all 4 (title card, classroom wide, teacher close-up, crumple/END).

## Medium determination
**Hand-drawn digital sketch ink, black-and-white, with one graphic-design title card.**
Evidence: scratchy variable pen strokes with visible overdraw on hair and stripes;
scribbled hatching left raw; background figures drawn then knocked back to pale gray
line (a digital layer-opacity move); the title card is the outlier — typeset-feeling
block lettering with drop shadow and stock-style evolution silhouettes, i.e. a
designed card, not a drawn panel. No photo texture, no AI artifacts, no 3D shading.

## Line / color / shading / lettering
- **Line:** rough, fast, scratchy pen; heavy reworked contours on the subject; energy
  over cleanliness. Speed lines radiate from the crumple impact in panel 4.
- **Color:** none in the story panels — pure black ink on white. The only color in the
  strip is the blue AUTOBIOGRAPHY title lettering.
- **Shading:** scribble-hatch on hair, sweater, shadows; depth achieved by fading
  background linework to ghost gray rather than by tone; large white negative space.
- **Lettering:** hand-lettered all-caps caption narration along the top edge of each
  panel; floating "BLAH BLAH BLAH" stack beside the silhouette head; chunky END at
  bottom-right; title card uses bold display lettering with offset shadow.

## Palette table
| Name | Hex est. | Where used |
|---|---|---|
| ink_black | #111111 | linework, teacher silhouette, evolution figures, shirt stripes, END |
| paper_white | #ffffff | page ground everywhere |
| ghost_gray | #c4c4c4 | faded background figures and classroom clutter |
| mid_gray | #8a8a8a | globe, sweater stripe fills, sparse shadow fills |
| title_blue | #4a7fd1 | AUTOBIOGRAPHY lettering only |

## Composition & framing habits
- Subject-foreground / ghost-background layering: whoever matters is full black ink,
  everyone else fades.
- The teacher enters as a solid black silhouette filling the right third (over-the-
  shoulder menace), then gets a dead-on looming close-up from slightly below.
- Final panel uses a diagonal arm thrust from frame right with speed lines — the only
  burst of motion in an otherwise still strip.
- Caption narration is structural: every story panel carries a top caption strip;
  the voiceover/art split is memoir voice over child POV.

## Continuity risks
1. The title card and the story panels are two different visual systems — keep them
   separate; do not let the card's clean graphic style bleed into the sketch panels.
2. Boy's identity anchors: shaggy mop + freckles + striped tee; stripes must stay
   horizontal black bands.
3. Teacher must read identically as silhouette (panel 2) and as drawn face (panel 3):
   bun + cat-eye glasses + pointer stick are the silhouette-legible keys.
4. Ghost-gray background fade is easy to lose — engines tend to render backgrounds at
   full weight or full tone.
5. Blue must not leak into story panels.

## Keep vs fix (for regeneration)
**Keep:** scratchy raw pen energy; white-paper staging; ghost-gray background fade;
silhouette-first teacher reveal; top-strip caption narration; speed-line crumple beat;
END card; blue-on-white designed title card as its own asset.
**Fix:** generate story panels textless, letter captions in post; build the title card
as a layout/typography pass, not an image-gen pass; model-sheet the teacher in both
silhouette and face form; pin the boy's stripe count and hair mass; explicitly prompt
"background figures in faint pale gray line only".
