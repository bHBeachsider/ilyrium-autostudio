# Style Analysis — Holy S*** It's Cody

Seed analysis from source panels 01, 04, 07 (of 7). Date: 2026-06-11.

## Medium determination

**Hand-drawn digital, pure black-and-white pen-and-ink doodle.** Evidence:

- Thin, scratchy, ballpoint-weight line with visibly shaky strokes (panel 01: grill hood drawn in four wobbly rectangles; Cody's hair is scribble-hatch). This is deliberate naive cartooning, not unfinished work — faces carry precise comic exaggeration (Cody's enormous drooping nose, boss's beak profile) inside the crude line.
- No grays anywhere in the artwork: the value system is binary. Distance/drama handled by flipping figures to SOLID black silhouette (panel 04: both runners; panel 07: onlookers' heads and the two huge smoke columns).
- Square 1024x1024 panels (different aspect from other Broderick strips).
- Title is the one typeset element: a gray stencil-serif display face.

## Line / color / shading / lettering

- **Line:** thin, scratchy, uniform-thin pen line; scribble-hatch for hair, awnings, texture; props are minimal stroke-count doodles (cloud = two bumps, window = two slashes).
- **Color:** none. Strict black on white.
- **Shading:** none. Solid black silhouette fill substitutes for all tone and atmosphere.
- **Lettering:** marker-weight hand caps floating free, no balloons, positioned near the speaker's side of the frame; stacked dialogue reads top-down; "END" small hand caps lower right; typeset gray stencil title on panel 1 only.

## Palette table

| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | everything unrendered — walls, sky, street |
| pen_ink_black | #1A1A1A | contour lines, hatching, dialogue lettering |
| silhouette_black | #000000 | solid-fill figures, smoke columns, boots, band tee |
| title_stencil_gray | #8C8C8C | typeset title card lettering (panel 1 only) |

## Composition and framing habits

- Square panels with dialogue in the top third, figures in the lower two-thirds, generous white margins.
- Eye-level medium two-shots for kitchen scenes; wide shots for street scenes with a low doodled skyline and a single cloud.
- Silhouette grammar: full-black figures signal motion (sprint) or rear-view POV (watching the fire); line-drawn figures carry expression.
- The GOLDEN FRY sign with dancing fry-cup mascot is a recurring landmark — appears intact (panel 4) then half-consumed by smoke (panel 7) for the payoff.
- Punchline staging: catastrophe rendered huge (smoke columns fill half the frame), humans tiny.

## Continuity risks

1. **Crudeness drift** — generators will clean up the line and add tone; the shaky thin line and binary value system must be enforced every shot.
2. **Cody's nose** — the single most identifying feature; must stay enormous and drooping in every angle.
3. **Silhouette discipline** — silhouettes must still read as the right characters (bowl cut vs stringy hair vs paper hat outlines).
4. **GOLDEN FRY signage** — hand-lettered logo and mascot must match between panels 4 and 7.
5. **Square aspect** — this strip is 1:1, unlike the landscape Broderick strips; keep aspect consistent within the project.

## Keep vs Fix (for regeneration)

**Keep:**
- Binary black/white value system, zero midtones
- Scratchy thin line + scribble hatch
- Solid-silhouette grammar for motion and rear views
- Floating hand-lettered caps, no balloons
- Huge-catastrophe / tiny-people punchline staging
- Square panel format

**Fix:**
- Inconsistent figure scale between panels (boss shrinks notably between 1 and 7) — lock relative heights on a model sheet
- The typeset gray title sits oddly with the hand-made interior lettering — keep title as a fixed asset composited in post
- Lettering should be a post pass; never generated
