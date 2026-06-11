# Style Analysis — Snapshots of Life No.707B (Autobiography)

Seed analysis from source panels 01, 04, 05, 06 (of 6). Date: 2026-06-11.

## Medium determination

**Hand-drawn digital, grayscale with disciplined spot color.** Evidence:

- Panel 05: Schpiegler's head is densely worked caricature — pen-textured graying beard, squeezed-shut eyes behind heavy black rectangular glasses, flying sweat droplets — clearly drawn, with consistent exaggeration across panels 05 and 06 (no AI anatomy drift; the ghosted corner bust in 06 matches the panel-05 head).
- Bodies and environments drop fidelity deliberately: scribbled weed banks and a loose one-point-perspective road (panel 04), quick pegboard and cabinet lines (05), bare bench corner (06).
- Title card (panel 01) is a graphic-design composite: ornate green script, bold serif "No.707B", and a stock-style ascent-of-man silhouette strip ending in a slouching drinker — flat graphic shapes, not drawing.
- Spot color used twice, surgically: green title lettering; bright red blood accents in the final panel (the only color in the scene).

## Line / color / shading / lettering

- **Line:** variable — dense fine pen texture on faces/beard; medium contour on figures; loose scribble for vegetation; ruler-straight panel borders and caption boxes.
- **Color:** grayscale base. Two spot breaks: title_green script (panel 01), blood_red accents (panel 06).
- **Shading:** soft gray washes on garments and sky; flat mid-gray fills (road sign, shirt); solid black silhhouettes for the industrial skyline and smoke; a ghosted pale-gray figure rendering for the remembered teacher.
- **Lettering:** white rounded caption boxes with black borders anchored top of panel, filled with bold italic hand caps; emphasis via heavier weight and larger size mid-sentence (CLUCK CLUCK CLUCK!); footnote asides in smaller caps; boxed END card lower right; in-art signage hand-lettered (WELCOME TO NEW JERSEY "THE GAWDEN STATE", bumper sticker).

## Palette table

| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | backgrounds, caption boxes, walls |
| ink_black | #1A1A1A | contours, lettering, glasses, box borders |
| wash_light_gray | #DCDCDC | garments, sky band, ghosted memory bust |
| wash_mid_gray | #A9A9A9 | work shirt, sign plate, road, shadows |
| silhouette_black | #111111 | skyline, smoke, evolution title figures |
| title_green | #2F9E2F | series-title script only (panel 01) |
| blood_red | #CC2222 | fingertip, roller smear, bench drips (panel 06 only) |

## Composition and framing habits

- Bordered landscape panels; caption box pinned across the top of nearly every panel — the memoir voiceover drives the strip.
- Caricature antagonist staged BIG: fills the left half of frame, pointing diagonals, sweat droplets as rage radiata.
- Kids underplay: faint smirk, flat hands — the comedy is the asymmetry of energy.
- One scene-setting wide (panel 04): low rear view, one-point perspective road, silhouette skyline, in-art signage carrying the gag.
- Memory grammar: ghosted pale-gray bust in the upper corner for the remembered glowering teacher (panel 06).
- END in a small boxed card lower right.

## Continuity risks

1. **Schpiegler's head** — beard density, glasses shape, and sweat droplets are the strip's identity; must match across angry/ghosted renditions.
2. **Spot-color discipline** — red and green must never leak beyond their designated panels; generators love to colorize.
3. **Caption-box system** — consistent box geometry and lettering style across all panels; build as a post-pass template.
4. **Sensitive content** — scene 3's rumor flashback (white pointed hood) is a deliberate damning gag about the character; render as the generic costume described in scenes.json, never add real-world insignia (negatives enforce). Flag for operator review before publication.
5. **In-art signage** — NJ sign and bumper sticker are punchlines; letter in post.

## Keep vs Fix (for regeneration)

**Keep:**
- Grayscale + surgical spot color (green title / red blood)
- Densely-rendered caricature head vs loose everything-else hierarchy
- Top-anchored caption boxes with bold italic emphasis lettering
- Ghosted-figure memory grammar
- Silhouette skyline and graphic title-card composite

**Fix:**
- Narrator's face wobbles between panels 05 and 06 (nose length, hair mass) — lock a model sheet
- Caption box line-weight varies — standardize the template
- All lettering (captions, signage, END) as post passes
- Title-card silhouettes should be redrawn as original art, not stock-resembling assets
