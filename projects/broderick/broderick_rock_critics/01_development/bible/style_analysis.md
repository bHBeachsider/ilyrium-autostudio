# Style Analysis — Rock Critics (SEED v0, 2026-06-11)

Panels sampled: all 3 (01 Darby Crash lecture w/ silhouette listener, 02 couch rant, 03 "SHOW" loop + END). Panel 01 doubles as the dialogue-heavy sample.

## Medium Determination
**Hand-drawn digital, raw expressive pen sketch, strict grayscale, square format.** Evidence:
- Nervous, scratchy contour with visible overdrawn strokes and construction wobble (hands, couch edges, hair) — unmistakably hand-laid; no AI smoothness, no photo texture.
- Grotesque caricature pushed hard: sagging faces, enormous drooping noses, sunken eyes — an editorial-cartoon sensibility, looser and uglier-on-purpose than the other Broderick strips.
- Flat digital gray washes dropped under the line (uniform value, hard edges); heavy solid-black shapes used as compositional anchors.
- Lettering is typeset all-caps comic font with underline emphasis (DIVIDED, HAD, THE) — digital lettering pass.
- Panels are square (1:1), unlike the landscape strips.

## Line / Color / Shading / Lettering
- **Line:** Raw, fast, expressive; thin scratchy interior detail against thick black masses; smoke drawn as a loose spiral squiggle; hatch scribbles for couch wear (##) and stubble.
- **Color:** None. White, near-black, two flat grays.
- **Shading:** Mostly flat wash planes; scribble-hatching for texture rather than form; black solids (tee, boots, silhouette) carry the value structure.
- **Lettering:** Typeset all-caps comic font in borderless caption blocks pressing down from the panel top; underlines for emphasis; in panel 03 the text wall occupies ~40% of the square and visually crushes the shrunken figure — text-as-composition is in-style. Bordered "END" plate, lower right.

## Palette Table
| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | Background, caption zones, wall faces |
| ink_black | #111111 | Band tee, silhouette listener, boots, window grille, lettering |
| wash_gray_light | #C9C9C9 | Couch, jacket/cardigan, table |
| wash_gray_mid | #9A9A9A | Hair mass, shadow planes, floor corners |
| tee_logo_white | #F2F2F2 | Faded club lettering knocked out of the black tee |

## Composition & Framing Habits
- Square panels; figure pushed low or off-center with caption text owning the top band.
- Panel 01: over-the-shoulder framing with foreground black silhouette head (recurring Broderick device — mute listener as framing wall); floating "?" over the silhouette.
- Panel 02: low-angle medium shot, figure straddling the couch back, diagonal energy matching the rant crescendo.
- Panel 03: figure shrunk and hunched at bottom, text wall pressing down — composition mirrors psychological state.
- Minimal set: couch, leaded window grille, smoke squiggle; the room is implied, not built.

## Continuity Risks
1. **Major: the critic is off-model between source panels** — panel 01 reads elderly/bespectacled, panel 02 scrawnier and bare-faced, panel 03 heavier with glasses again. A locked model sheet must override the source variance; pick the canonical face (thin, frizzy thinning hair, stubble, manic eyes, long drooping nose) and hold it.
2. The black club tee logo: keep it a faded generic punk-club mark; generators must not render a real trademark legibly.
3. The silhouette listener must stay featureless solid black — same convention as the biodome strip's silhouette man.
4. Square aspect must be preserved; landscape re-staging changes the text-pressure compositions.
5. Grayscale discipline; no color drift.
6. Text-wall panels need post-lettering — 30+ repetitions of "SHOW" will shred in-render.

## Keep vs Fix (for regeneration)
**Keep:**
- Raw scratchy pen line and grotesque caricature energy.
- Black-mass anchors (tee, boots, silhouette) against white and flat grays.
- Square format with caption band on top; text-as-crushing-weight punchline composition.
- Foreground silhouette listener framing device; smoke squiggle prop.
- Underline emphasis in lettering.

**Fix:**
- Lock the critic's face — source drifts wildly off-model panel to panel (the single biggest regeneration risk).
- Normalize wash values; couch gray and jacket gray swap between panels.
- Panel 03 source is low-resolution (768px); regenerate at working res from the model sheet, not from the panel.
- Generic-ize the tee logo to a consistent invented club mark and reuse the exact asset.
