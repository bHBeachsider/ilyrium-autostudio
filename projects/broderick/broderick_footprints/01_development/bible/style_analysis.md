# Style Analysis — Footprints on the Beach (SEED v0, 2026-06-11)

Panels sampled: both panels (entire strip). Panel 01 = poem setup (text-heavy), panel 02 = wordless punchline + END.

## Medium Determination
**Hand-drawn digital, strict grayscale.** Evidence:
- Loose wobbling hand-ink contours on shoreline, wave squiggles, net mesh, and figures — no vector cleanliness, no photo texture, no AI-render smoothness.
- Sand is untouched white paper with sparse squiggle marks; sea and mountains are flat hard-edged gray bands — graphic, not environmental rendering.
- Footprints are solid black graphic stamps, scaled by perspective but not modeled.
- Figures in panel 02 are scribble-hatched sketch figures with minimal faces.
- Narration in panel 01 is calligraphic serif italic with an ornate illuminated drop-cap O — a deliberate devotional-greeting-card typographic costume, distinct from every other Broderick strip.

## Line / Color / Shading / Lettering
- **Line:** Loose, confident, medium-thin; squiggle shorthand for waves and sand texture; scribble-hatch for the volleyball net and robe shading; sun drawn as a circle with radiating dash strokes.
- **Color:** None. White, near-black, and three flat grays (sea, mountains, robe/net).
- **Shading:** Flat band values only; no form modeling; scribble-hatch as texture.
- **Lettering:** Panel 01 — calligraphic italic serif body text with illuminated drop-cap, filling the top half (typography as parody costume). Panel 02 — no text except a large loose hand-scrawled END. No balloons anywhere.

## Palette Table
| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | Sky and sand — dominant field in both panels |
| ink_black | #111111 | Footprint trails, hair/beard, swimsuits, drop-cap, END |
| sea_gray | #9C9C9C | Flat ocean band across the upper-middle of both panels |
| mountain_gray | #B5B5B5 | Distant range, panel 01 |
| robe_pale | #E6E6E6 | The Lord's robe, net shading, cloud/wave accents |

## Composition & Framing Habits
- Very wide landscape frames (4:3 source, panoramic feel); high flat horizon with stacked value bands (white sky / gray sea / white sand).
- Panel 01: text owns the top half; the image is the bottom half — two black footprint trails receding in one-point perspective toward the surf.
- Panel 02: full-frame tableau; volleyball net slices the frame diagonally; figures mid-action; END bottom right.
- Two-panel rhythm: reverent text-heavy setup, then total silence for the visual punchline — the page-turn IS the joke.

## Continuity Risks
1. **scenes.json premise drift:** scene 2 describes "ladder-like pole structures" and a "dark boulder / drag groove" on an empty beach — the actual panel shows the Lord (bearded, robed) spiking a volleyball at a net with two bikini-clad women players. The "ladders" are the volleyball net poles misread. scenes.json scene 2 needs a re-parse before shot specs are generated.
2. characters.md claims the Lord is "never shown in person" — contradicted by panel 02; casting canon updated to describe him as drawn (robed, bearded, mid-spike). Keep the dreamer off-screen.
3. The devotional calligraphic typography in panel 01 is load-bearing parody — substituting comic-font caps would kill the joke.
4. The Lord must stay deadpan-mundane: no halo, no glow, no divine lighting; the gag depends on flat rendering.
5. Footprints are solid black stamps — generators will soften them into realistic impressions; keep graphic.
6. Grayscale discipline; no sunset color drift on the beach.

## Keep vs Fix (for regeneration)
**Keep:**
- White-paper sand + flat gray sea/mountain bands; squiggle wave shorthand.
- Solid black footprint trails in one-point perspective.
- Calligraphic devotional typography with illuminated drop-cap for the poem panel.
- Wordless full-frame punchline with hand-scrawled END.
- Dash-stroke sun, scribble-hatched net and robe.

**Fix:**
- Re-parse scenes.json scene 2 to match the actual volleyball punchline before bridging to shot specs.
- Net mesh hatching is irregular panel-internally — lock a single hatch density.
- Figure faces in panel 02 are barely resolved — model-sheet the Lord and the two players if the punchline is held longer than a beat in video.
- Poem text must be lettered in post (long body text will shred in-render).
