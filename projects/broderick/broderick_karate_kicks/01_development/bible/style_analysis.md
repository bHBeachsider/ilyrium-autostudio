# Style Analysis — Karate Kicks (SEED v0, 2026-06-11)

Panels examined: 01 (dinner-table setup), 03 (Mr. Johnson ribbing, dialogue-heavy), 04 (first kick), 06 (final kick / cliffhanger). 6 panels total in `panels/`.

## Medium determination

**Vintage clip-art collage + digital lettering. NOT hand-drawn original art, NOT AI render.**

Evidence:
- Figures in panels 01 and 03 are unmistakably 1950s-era advertising/stock illustration: feathered pen-and-ink shading, crosshatched suit folds, idealized mid-century faces and poses (woman with teacup, man pointing and laughing with raised cup — classic stock poses).
- Faint residual stock-image watermarks are visible in panels 01, 03, and 04 (ghosted text/circles over the figures) — proof the art is lifted from a stock library, not drawn for the strip.
- The kicking husband in panels 04 and 06 is the **identical solid-black silhouette asset, reused pixel-for-pixel** between panels; only the victim figure is swapped. Asset-reuse collage, not redrawing.
- Lettering is a clean digital comic font (bold italic all-caps, BadaBoom/Komika family look), uniform across panels — typeset, not hand-lettered.
- Impact bursts and stars in 04/06 are the one loosely hand-scrawled element, drawn over the collage.

## Line / color / shading / lettering

- **Line:** vintage engraving-style pen-and-ink in the collaged figures — fine, confident, feathered hatching. Silhouettes have no internal line at all.
- **Color:** strictly monochrome. White ground, black ink, occasional soft gray photographic wash (Mrs. Johnson's suit in 06, faint drop shadows).
- **Shading:** crosshatch/feathering inside clip-art figures; flat fills for silhouettes; no gradients, no halftone dots.
- **Lettering:** free-floating blocks of bold italic caps, no speech balloons, no tails; speaker attribution purely by placement above/near the figure. Punchy short lines except panel 03's long monologue block.

## Palette table

| Name | Hex (est.) | Where used |
|---|---|---|
| paper_white | #FFFFFF | full background, all panels |
| ink_black | #1A1A1A | linework, lettering, silhouettes |
| halftone_gray | #B5B5B5 | tonal wash on collaged figures, shadows |
| watermark_ghost | #E8E8E8 | residual stock watermarks (artifact — remove) |
| impact_scrawl | #202020 | hand-drawn burst/star marks at kick impact |

## Composition & framing habits

- Square ~1:1 panels, borderless, floating on white.
- Text occupies top third; art occupies bottom two-thirds.
- Dialogue scenes: two-shot, waist-up, eye level, generous negative space between figures.
- Action scenes: fixed tableau — silhouette kicker on the left, victim upper-right with burst + stars, seated wife silhouette bottom-center foreground with table edge and wine glass. The composition repeats verbatim across kicks 1–3; the repetition IS the gag rhythm.

## Continuity risks

1. **Stock watermarks** will reappear or smear if panels are used as img2img seeds — must be cleaned or regenerated.
2. **Husband mode-switch** (drawn figure at table vs. pure silhouette in action) must be stated explicitly per prompt or models will draw a detailed kicker.
3. **Mrs. Johnson inconsistency** in the source: wavy light hair at the table (panel 2) vs. dark updo + skirt suit when kicked (panel 6). Pick one canon.
4. **Identical-silhouette reuse** is load-bearing for comedy; generating fresh poses per kick would break the deadpan rhythm.
5. Lettering font must stay uniform; any hand-lettered or balloon treatment breaks the meme-collage register.

## Keep vs Fix for regeneration

**Keep:**
- Monochrome vintage clip-art figure style with crosshatch shading
- Solid-black silhouette convention for the husband mid-kick and foreground wife
- Repeated action-tableau composition and scrawled impact bursts
- Free-floating bold italic caps lettering, no balloons
- Borderless square panels, heavy white space

**Fix:**
- Remove all residual stock watermarks
- Resolve Mrs. Johnson's hair/wardrobe to a single design
- Standardize gray-wash usage (currently inconsistent between collage sources)
- Slightly unify line weight across collaged figures (different stock sources have different stroke density)
